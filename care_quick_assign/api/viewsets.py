from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

# from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from pydantic import UUID4, BaseModel

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRTagMixin,
    EMRUpdateMixin,
)
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
    TokenBookingReadSpec
)

from care.utils.time_util import care_now


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
                # Failsafe to prevent infinite loop
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





class AutoAssignmentSpec(BaseModel):
    patient: UUID4
    facility: UUID4


class QuickAutoAssignViewSet(
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
    EMRTagMixin,
):  
    @classmethod
    def get_slots_for_day_handler(cls, availabilities, exceptions, schedulable_resources, day):
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
            calculated_dow_availabilities, exceptions, day
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


    
    @classmethod
    def get_first_best_slot_handler(cls, facility_obj, window_size):
        schedulable_resources = SchedulableResource.objects.filter(
            facility=facility_obj,
            resource_type = SchedulableResourceTypeOptions.practitioner.value
        )

        if not schedulable_resources:
            raise ValidationError("No schedules found for any practitioner")

        current_timestamp = timezone.now()
        start_date = current_timestamp.date()
        end_date = start_date + timedelta(days=window_size)

        availabilities = Availability.objects.filter(
            slot_type = SlotTypeOptions.appointment.value,
            schedule__valid_from__lte = end_date,
            schedule__valid_to__gte = start_date,
            schedule__resource__in = schedulable_resources,
        )

        if not availabilities:
            raise ValidationError("No availability found for any practitioner")

        exceptions = AvailabilityException.objects.filter(
            resource__in = schedulable_resources,
            valid_from__lte=end_date,
            valid_to__gte=start_date,
        )

        for day_offset in range(window_size):
            day = start_date + timedelta(days=day_offset)

            availabilities_for_current_day = availabilities.filter(
                schedule__valid_from__lte=day,
                schedule__valid_to__gte=day
            )

            exceptions_for_current_day = exceptions.filter(
                valid_from__lte=day,
                valid_to__gte=day,
            )

            slots_for_current_day = cls.get_slots_for_day_handler(
                availabilities=availabilities_for_current_day,
                exceptions=exceptions_for_current_day,
                schedulable_resources=schedulable_resources,
                day=day
            )

            if not not slots_for_current_day :
                return slots_for_current_day.first()

        return None




    @classmethod
    def create_appointment_handler(cls, slot_obj, patient_obj, user):
        with transaction.atomic():
            if (
                TokenBooking.objects.filter(
                    patient = patient_obj,
                    token_slot__start_datetime__gte = care_now()
                )
                .exclude(status__in=COMPLETED_STATUS_CHOICES)
                .count()
                >= settings.MAX_APPOINTMENTS_PER_PATIENT
            ):
                error = f"Patient already has maximum number of appointments ({settings.MAX_APPOINTMENTS_PER_PATIENT})"
                raise ValidationError(error)

            if not patient_obj:
                raise ValidationError("Patient not found")

            note = "This appointment was automatically generated using quick auto-assign feature."
            appointment = lock_create_appointment(slot_obj, patient_obj, user, note)

            return appointment



    
    @action(detail=False, methods=["post"])
    def quick_auto_assign(self, request, *args, **kwargs):
        request_data = AutoAssignmentSpec(**request.data)
        
        patient = Patient.objects.filter(external_id=request_data.patient).first()
        facility = Facility.objects.filter(external_id=request_data.facility).first()

        window_size = settings.WINDOW_SIZE_FOR_AUTO_ASSIGNMENT

        if not window_size or window_size < 1:
            raise ValidationError("Invalid window size")

        slot_obj = self.get_first_best_slot_handler(facility, window_size)

        if not slot_obj:
            raise ValidationError("No slot found for auto-assignment")

        appointment = self.create_appointment_handler(
            slot_obj, patient, request.user
        )

        return Response(TokenBookingReadSpec.serialize(appointment).to_json())

    @action(detail=False, methods=["get"])
    def hello(self, request, *args, **kwargs):
        return Response({"message": "Hello from care_quick_assign plugin!"})