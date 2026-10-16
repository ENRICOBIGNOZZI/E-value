"""Response-independent two-block adjudication; selections and criteria are distinct."""
from dataclasses import dataclass


@dataclass
class Opportunity:
    onset: int
    kind: str
    confirmed: bool=False
    confirmation_day: int=-1
    criterion_day: int=-1
    selected_day: int=-1
    termination_day: int=-1
    termination_reason: str=''


class EventTracker:
    def __init__(self,metadata,tolerance):
        self.metadata=metadata.copy();self.tolerance=tolerance
        self.previous_mean=None;self.run=None;self.rows=[];self.unstable_runs=0
        self.next_event=0

    def observe(self,day,mean,eligible=False,selected=False):
        positive=mean>self.tolerance
        if positive:
            if self.run is None:
                self.run=Opportunity(day,'inception_positive' if self.previous_mean is None else 'sign_change_positive')
            elif not self.run.confirmed:
                self.run.confirmed=True;self.run.confirmation_day=day
            if eligible and self.run.criterion_day<0:self.run.criterion_day=day
            if selected and self.run.selected_day<0:self.run.selected_day=day
        elif self.run is not None:
            if self.run.confirmed:self._finish(day,'sign_reversal')
            else:self.unstable_runs+=1;self.run=None
        self.previous_mean=mean

    def close(self,day,reason):
        if self.run is None:return False
        self.run.termination_day=day;self.run.termination_reason=reason
        if self.run.confirmed:
            self._finish(day,reason);return False
        return True  # Follow the unchanged shadow pair for one additional block.

    def adjudicate(self,day,mean):
        if self.run is None or self.run.confirmed or self.run.termination_day<0:
            raise ValueError('No closed pending opportunity to adjudicate')
        if mean>self.tolerance:
            self.run.confirmed=True;self.run.confirmation_day=day
            self._finish(self.run.termination_day,self.run.termination_reason)
        else:self.unstable_runs+=1;self.run=None

    def _finish(self,day,reason):
        run=self.run
        if not run.confirmed:raise ValueError('Unconfirmed event cannot enter the stable-event denominator')
        self.next_event+=1
        self.rows.append(dict(**self.metadata,event_index=self.next_event,onset_day=run.onset,
            event_kind=run.kind,confirmation_day=run.confirmation_day,
            criterion_day=run.criterion_day,selected_day=run.selected_day,
            termination_day=day,termination_reason=reason,
            criterion_detected=run.criterion_day>=0,selected=run.selected_day>=0,
            criterion_delay_days=run.criterion_day-run.onset if run.criterion_day>=0 else -1,
            selection_delay_days=run.selected_day-run.onset if run.selected_day>=0 else -1))
        self.run=None
