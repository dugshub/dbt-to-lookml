# Domain Layer

Our semantic primitives - the core business concepts.

## Current Structure (Simple)

```
domain/
├── measure.py      # Measure + AggregationType
├── dimension.py    # Dimension + DimensionType
├── metric.py       # Metric + MetricVariant + types
└── model.py        # ProcessedModel, Entity
```

## Future Growth Path

When adding storage layer / UI management, expand to feature-folder pattern:

```
domain/
├── measure/
│   ├── schema.py       # Pydantic (current measure.py)
│   ├── types.py        # Enums
│   ├── models.py       # SQLAlchemy models
│   ├── service.py      # CRUD operations
│   └── repository.py   # Complex queries
├── dimension/
│   └── ...
├── metric/
│   └── ...
└── model.py
```

Reference: pattern-stack/backend-patterns atomic architecture.
