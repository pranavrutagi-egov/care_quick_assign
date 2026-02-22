import logging
from datetime import datetime, time, timedelta

from celery import shared_task

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from care_quick_assign.settings import plugin_settings

from care_quick_assign.models.assignment_status import AutoAssignmentEvent

from care.emr.api.viewsets.scheduling import lock_create_appointment

from care.emr.models import (
    AvailabilityException,
    TokenSlot
)
from care.emr.models.patient import Patient
from care.facility.models.facility import Facility
from care.emr.models.scheduling import SchedulableResource, TokenBooking
from care.emr.models.scheduling.schedule import Availability

from care.emr.resources.scheduling.schedule.spec import (
    SchedulableResourceTypeOptions,
    SlotTypeOptions
)
from care.emr.resources.scheduling.slot.spec import (
    COMPLETED_STATUS_CHOICES,
)

from care.utils.time_util import care_now


logger = logging.getLogger(__name__)


@shared_task
def create_quick_assignment(patient_external_id):
    patient = Patient.objects.filter(external_id=patient_external_id).first()

    if not patient:
        logger.warning("Patient with external_id %s not found.", patient_external_id)
        return

    assignment_event_log, _ = AutoAssignmentEvent.objects.get_or_create(patient=patient)

    try:
        facility = Facility.objects.filter(geo_organization=patient.geo_organization).first()

        if not facility:
            assignment_event_log.log_failure("No facility found for patient assignment")
            return

        first_best_slot = get_first_best_slot_handler(facility)

        if not first_best_slot:
            window_size = plugin_settings.CARE_WINDOW_SIZE_FOR_AUTO_ASSIGNMENT
            assignment_event_log.log_failure(
                f"No suitable slot found within {window_size} day{'s' if window_size != 1 else ''} for quick assignment"
            )
            return

        appointment = create_appointment_handler(
            slot=first_best_slot,
            patient=patient,
            user=patient.created_by
        )

        assigned_staff = appointment.token_slot.resource.user
        assignment_event_log.log_success(assigned_staff=assigned_staff)


    except Exception as e:
        assignment_event_log.log_failure(str(e))
        retry_quick_assignment(patient_external_id)



def get_first_best_slot_handler(facility):
    schedulable_resources = SchedulableResource.objects.filter(
        facility=facility,
        resource_type=SchedulableResourceTypeOptions.practitioner.value,
    )

    if not schedulable_resources.exists():
        raise Exception("No schedulable resources found for the given facility")

    window_size = plugin_settings.CARE_WINDOW_SIZE_FOR_AUTO_ASSIGNMENT

    if not window_size or window_size < 1:
        raise ValidationError("Invalid window size for auto-assignment")

    current_timestamp = timezone.now()
    start_date = current_timestamp.date()
    end_date = start_date + timezone.timedelta(days=window_size)

    availabilities = Availability.objects.filter(
        slot_type=SlotTypeOptions.appointment.value,
        schedule__valid_from__lte=end_date,
        schedule__valid_to__gte=start_date,
        schedule__resource__in=schedulable_resources,
    )

    if not availabilities:
        raise Exception("No availabilities found for the given resources")

    exceptions = AvailabilityException.objects.filter(
        resource__in=schedulable_resources,
        valid_from__lte=end_date,
        valid_to__gte=start_date,
    )

    for day_offset in range(window_size):
        day = start_date + timezone.timedelta(days=day_offset)

        availabilities_for_current_day = availabilities.filter(
            schedule__valid_from__lte=day,
            schedule__valid_to__gte=day,
        )

        exceptions_for_current_day = exceptions.filter(
            valid_from__lte=day,
            valid_to__gte=day,
        )

        slots_for_current_day = get_slots_for_day_handler(
            availabilities=availabilities_for_current_day,
            exceptions=exceptions_for_current_day,
            schedulable_resources=schedulable_resources,
            day=day,
        )

        if slots_for_current_day.exists():
            logger.info(f"Slots found for day {day}")
            return slots_for_current_day.first()

    raise Exception(f"No suitable slot found within {window_size} day{'s' if window_size != 1 else ''} for quick assignment")



def get_slots_for_day_handler(availabilities, exceptions, schedulable_resources, day):
    calculated_dow_availabilities = []

    for schedule_availability in availabilities:
        for day_availability in schedule_availability.availability:
            if day_availability["day_of_week"] == day.weekday():
                calculated_dow_availabilities.append(
                    {
                        "availability": day_availability,
                        "slot_size_in_minutes": schedule_availability.slot_size_in_minutes,
                        "availability_id": schedule_availability.id,
                        "resource": schedule_availability.schedule.resource
                    }
                )

    slots = convert_availability_and_exceptions_to_slots(
        availabilities=calculated_dow_availabilities,
        exceptions=exceptions,
        day=day,
    )


    created_slots = TokenSlot.objects.filter(
        start_datetime__date=day,
        end_datetime__date=day,
        resource__in=schedulable_resources,
    )


    for slot in created_slots:
        slot_key = f"{timezone.make_naive(slot.start_datetime).time()}-{timezone.make_naive(slot.end_datetime).time()}"
        if (
            slot_key in slots
            and slots[slot_key]["availability_id"] == slot.availability.id
        ):
            slots.pop(slot_key)


    for _, slot in slots.items():
        end_datetime = datetime.combine(
            day, slot["end_time"], tzinfo=None
        )
        # Skip creating slots in the past
        if end_datetime < timezone.make_naive(timezone.now()):
            continue
        TokenSlot.objects.create(
            resource=slot["resource"],
            start_datetime=datetime.combine(
                day, slot["start_time"], tzinfo=None
            ),
            end_datetime=end_datetime,
            availability_id=slot["availability_id"],
        )


    slots = TokenSlot.objects.filter(
        start_datetime__date=day,
        end_datetime__date=day,
        resource__in=schedulable_resources,
        allocated__lt=F("availability__tokens_per_slot")
    ).select_related(
        "availability",
        "availability__schedule"
    ).order_by(
        "start_datetime"
    )

    return slots




def convert_availability_and_exceptions_to_slots(availabilities, exceptions, day):
    slots = {}
    for availability in availabilities:
        start_time = datetime.combine(
            day,
            time.fromisoformat(availability["availability"]["start_time"]),
            tzinfo=None,
        )
        end_time = datetime.combine(
            day,
            time.fromisoformat(availability["availability"]["end_time"]),
            tzinfo=None,
        )
        slot_size_in_minutes = availability["slot_size_in_minutes"]
        availability_id = availability["availability_id"]
        resource = availability["resource"]
        current_time = start_time
        i = 0
        while current_time < end_time:
            i += 1
            if i == settings.MAX_SLOTS_PER_AVAILABILITY + 1:
                break

            conflicting = False
            for exception in exceptions:
                exception_start_time = datetime.combine(
                    day, exception.start_time, tzinfo=None
                )
                exception_end_time = datetime.combine(
                    day, exception.end_time, tzinfo=None
                )
                if (
                    exception_start_time
                    < (current_time + timedelta(minutes=slot_size_in_minutes))
                ) and exception_end_time > current_time:
                    conflicting = True

            if not conflicting:
                slots[
                    f"{current_time.time()}-{(current_time + timedelta(minutes=slot_size_in_minutes)).time()}"
                ] = {
                    "start_time": current_time.time(),
                    "end_time": (
                        current_time + timedelta(minutes=slot_size_in_minutes)
                    ).time(),
                    "availability_id": availability_id,
                    "resource": resource
                }

            current_time += timedelta(minutes=slot_size_in_minutes)
    return slots



def create_appointment_handler(slot, patient, user):
    with transaction.atomic():
        if (
            TokenBooking.objects.filter(
                patient = patient,
                token_slot__start_datetime__gte = care_now()
            )
            .exclude(status__in=COMPLETED_STATUS_CHOICES)
            .count()
            >= settings.MAX_APPOINTMENTS_PER_PATIENT
        ):
            error = f"Patient already has maximum number of appointments ({settings.MAX_APPOINTMENTS_PER_PATIENT})"
            raise ValidationError(error)

        if not patient:
            raise ValidationError("Patient not found")

        note = plugin_settings.CARE_AUTO_ASSIGNMENT_APPOINTMENT_NOTE
        appointment = lock_create_appointment(slot, patient, user, note)

        return appointment



def retry_quick_assignment(patient_external_id):
    try:
        assignment_event_log = AutoAssignmentEvent.objects.get(
            patient__external_id=patient_external_id
        )

        if assignment_event_log.retry_count >= plugin_settings.CARE_QUICK_AUTO_ASSIGN_MAX_RETRIES:
            logger.warning(
                "Max retry attempts reached for patient %s. Current retry count: %d",
                patient_external_id,
                assignment_event_log.retry_count
            )
            return

        assignment_event_log.retry_count += 1
        assignment_event_log.save()

        transaction.on_commit(
            lambda: create_quick_assignment.delay(patient_external_id)
        )


    except AutoAssignmentEvent.DoesNotExist:
        logger.warning("No assignment event log found for patient with external_id %s.", patient_external_id)
    except Exception as e:
        logger.error("Error while retrying quick assignment for patient with external_id %s: %s", patient_external_id, str(e))
