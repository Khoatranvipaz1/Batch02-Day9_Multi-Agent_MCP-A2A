# Stage 5 A2A Request Sequence

```mermaid
sequenceDiagram
    participant U as User/Test Client
    participant C as Customer Agent :10100
    participant R as Registry :10000
    participant L as Law Agent :10101
    participant T as Tax Agent :10102
    participant P as Compliance Agent :10103

    U->>C: A2A legal question
    C->>R: discover("legal_question")
    R-->>C: Law Agent endpoint
    C->>L: A2A message, depth=1
    L->>L: Analyze law and route
    par Tax branch
        L->>R: discover("tax_question")
        R-->>L: Tax Agent endpoint
        L->>T: A2A message, depth=2
        T-->>L: Tax analysis
    and Compliance branch
        L->>R: discover("compliance_question")
        R-->>L: Compliance Agent endpoint
        L->>P: A2A message, depth=2
        P-->>L: Compliance analysis
    end
    L->>L: Aggregate analyses
    L-->>C: Comprehensive legal response
    C-->>U: Final response
```

The same `trace_id` and `context_id` are propagated through every A2A hop.
The verified E2E request completed in 44.21 seconds with Tax and Compliance
running concurrently.
