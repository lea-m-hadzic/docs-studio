# API reference

What `using Lattice` gives you. Anything not listed is internal.

## `PeriodicStructure`

```text
PeriodicStructure(; cell, sites, charges) -> PeriodicStructure
```

An immutable periodic structure in two or three dimensions.
[Defining a structure](usage.md) lists the constraints the constructor enforces; each
failure raises `ArgumentError` naming the field and the value.

Fields are `cell`, `sites`, `charges` and `dimension`.

## `latticesum`

```text
latticesum(structure; splitting = balanced(structure), tolerance = 1e-10,
           maxshells = 64, maxvectors = 20_000) -> LatticeSum
```

Evaluates the lattice sum for `structure`, raising its cut-offs until the error bound
falls under `tolerance` or a limit is reached. Never raises on non-convergence;
inspect `converged` instead.

`splitting` changes only the cost, never the answer beyond `tolerance`. `maxshells`
and `maxvectors` are there to bound the work on a pathological structure.

## `balanced`

```text
balanced(structure) -> Float64
```

The splitting parameter that gives the two parts roughly equal work. The default for
`latticesum`, and a reasonable starting point for timing experiments. See
[Choosing the splitting](certificate.md#choosing-the-splitting).

## `LatticeSum`

The result type. All fields are read-only.

| Field | Type | Meaning |
| --- | --- | --- |
| `value` | `Float64` | the sum, self-term excluded |
| `bound` | `Float64` | upper bound on the truncation error |
| `converged` | `Bool` | whether `bound <= tolerance` |
| `self` | `Float64` | the self-term, subtracted and reported |
| `real_part` | `Float64` | the real-space half, for diagnosis only |
| `reciprocal_part` | `Float64` | the reciprocal half, for diagnosis only |
| `shells` | `Int` | real-space shells used |
| `vectors` | `Int` | reciprocal vectors used |
| `splitting` | `Float64` | the α actually used |

!!! info "Keep this page in step with the code"
    A test can parse the module's `export` block and fail when this page documents a
    name the package does not export. That check needs the package, so it belongs in
    the project's own suite rather than in `docs-studio check`.
