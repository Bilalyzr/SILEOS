"""Data-only lab authoring contract; never execute uploaded expressions or HTML."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConceptCard(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=100)
    group: str = Field(min_length=1, max_length=80)
    explanation: str = Field(default='', max_length=600)


class LabHotspot(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,50}$')
    label: str = Field(min_length=1, max_length=100)
    label_ta: str = Field(default='', max_length=150)
    explanation: str = Field(default='', max_length=1200)
    explanation_ta: str = Field(default='', max_length=1600)
    position: list[float] = Field(min_length=3, max_length=3)

    @model_validator(mode='after')
    def coordinates(self):
        import math
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in self.position):
            raise ValueError('Hotspot coordinates must be between 0 and 1.')
        return self


class LabStep(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,50}$')
    kind: Literal['visit', 'parameter', 'question', 'observation']
    title: str = Field(min_length=1, max_length=160)
    title_ta: str = Field(default='', max_length=200)
    instruction: str = Field(default='', max_length=1600)
    instruction_ta: str = Field(default='', max_length=2000)
    hotspot_id: str | None = Field(default=None, max_length=50)
    parameter: Literal['rotation_y','scale','explode'] | None = None
    target_min: float = Field(default=0, ge=-180, le=180)
    target_max: float = Field(default=0, ge=-180, le=180)
    options: list[str] = Field(default_factory=list, max_length=6)
    correct_index: int | None = Field(default=None, ge=0, le=5)
    points: int = Field(default=0, ge=0, le=20)

    @model_validator(mode='after')
    def valid_step(self):
        if self.kind == 'question':
            if len(self.options) < 2 or any(not s.strip() or len(s)>300 for s in self.options) or self.correct_index is None or self.correct_index >= len(self.options):
                raise ValueError('Questions need 2-6 options and a valid correct answer.')
        elif self.options or self.correct_index is not None:
            raise ValueError('Answer options belong to question steps only.')
        if self.kind == 'visit' and not self.hotspot_id:
            raise ValueError('A visit step needs a hotspot.')
        if self.kind == 'parameter':
            bounds={'rotation_y':(-180,180),'scale':(0.5,2),'explode':(0,1)}
            if self.parameter not in bounds or not bounds[self.parameter][0] <= self.target_min <= self.target_max <= bounds[self.parameter][1]:
                raise ValueError('Set a valid target range for the selected model control.')
        if self.kind == 'observation' and self.points:
            raise ValueError('Observations are evidence for review and do not automatically earn marks.')
        return self


class ConceptLabConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    model_id: int | None = Field(default=None, gt=0)
    hotspots: list[LabHotspot] = Field(default_factory=list, max_length=30)
    guided_steps: list[LabStep] = Field(default_factory=list, max_length=30)
    assessment_enabled: bool = False
    concepts: list[str] = Field(default_factory=list, max_length=20)
    model_description: str = Field(default='', max_length=2000)
    model_description_ta: str = Field(default='', max_length=2500)
    engine: Literal['supplied', 'linear', 'projectile', 'pendulum', 'circuit', 'gas', 'wave', 'classification']
    source_slug: str | None = Field(default=None, max_length=50)
    objective: str = Field(min_length=10, max_length=1200)
    prediction: str = Field(min_length=5, max_length=600)
    investigation: list[str] = Field(min_length=1, max_length=8)
    explanation: str = Field(default='', max_length=3000)
    chapter_ids: list[str] = Field(default_factory=list, max_length=30)
    cards: list[ConceptCard] = Field(default_factory=list, max_length=30)

    @model_validator(mode='after')
    def check_content(self):
        if self.engine == 'supplied':
            from app.services.lab_catalog_service import CBSE_LABS
            if self.source_slug not in {l['slug'] for l in CBSE_LABS}:
                raise ValueError('Choose a supplied simulation.')
        if len({h.id for h in self.hotspots}) != len(self.hotspots) or len({s.id for s in self.guided_steps}) != len(self.guided_steps):
            raise ValueError('Hotspot and step identifiers must be unique.')
        if self.hotspots and not self.model_id:
            raise ValueError('Attach a model before adding hotspots.')
        for step in self.guided_steps:
            if step.kind in ('visit','parameter') and not self.model_id:
                raise ValueError('Model steps need an attached model.')
            if step.kind == 'visit' and step.hotspot_id not in {h.id for h in self.hotspots}:
                raise ValueError('A guided step references a missing hotspot.')
        if self.assessment_enabled and not any(s.points for s in self.guided_steps):
            raise ValueError('An assessment needs at least one scored step.')
        if any(not c.strip() or len(c)>100 for c in self.concepts):
            raise ValueError('Use concept names of 1-100 characters.')
        if any(not s.strip() or len(s) > 600 for s in self.investigation):
            raise ValueError('Investigation steps must contain 1–600 characters.')
        if len(set(self.chapter_ids)) != len(self.chapter_ids):
            raise ValueError('Chapter references must be unique.')
        from app.services.lab_studio_service import CHAPTER_IDS
        if any(c not in CHAPTER_IDS for c in self.chapter_ids):
            raise ValueError('Unknown curriculum chapter.')
        if self.engine == 'classification':
            if len(self.cards) < 3 or len({c.group for c in self.cards}) < 2:
                raise ValueError('Classification needs at least 3 cards and 2 groups.')
            if len({c.label.casefold() for c in self.cards}) != len(self.cards):
                raise ValueError('Card labels must be unique.')
        elif self.cards:
            raise ValueError('Cards belong to the classification engine only.')
        return self


class LabDraftIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=200)
    subject: Literal['science', 'mathematics', 'physics', 'chemistry', 'biology', 'general']
    description: str = Field(default='', max_length=2000)
    config: ConceptLabConfig


class LabPack(BaseModel):
    model_config = ConfigDict(extra='forbid')
    format: Literal['sasha-concept-labs']
    version: Literal[1]
    labs: list[LabDraftIn] = Field(min_length=1, max_length=30)


class NotebookIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    prediction: str = Field(default='', max_length=3000)
    observation: str = Field(default='', max_length=6000)
    conclusion: str = Field(default='', max_length=3000)
    trials: list[dict[str, str | float | int | bool]] = Field(default_factory=list, max_length=50)

    @model_validator(mode='after')
    def bounded_trials(self):
        import json
        if len(json.dumps(self.trials, allow_nan=False).encode()) > 30000:
            raise ValueError('Trial data exceeds 30 KB.')
        return self
