# Installation

## Requirements

- **Julia 1.11** or later. Continuous integration runs 1.11 and 1.12.
- No C toolchain. Every dependency is pure Julia.

## Install

!!! warning "Not in the General registry"
    `Lattice` is not registered, so `Pkg.add("Lattice")` will not find it. Install from
    a clone.

```bash
git clone https://github.com/example/Lattice.jl
cd Lattice.jl
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

`Pkg.instantiate()` installs the exact versions recorded in `Manifest.toml`. That is
the environment the method notes were written against, and it is what you want if you
are comparing numbers. To resolve fresh dependencies instead, delete `Manifest.toml`
first — and expect the last digits to move.

## Check the install

```bash
julia --project=. -e 'using Pkg; Pkg.test()'
```

The suite covers the structure constructors, both halves of the splitting, the bound,
and the published reference values for the square and face-centred cubic lattices. It
does not run anything that takes longer than a minute.

An end-to-end check:

```julia
using Lattice

square = PeriodicStructure(
    cell = [1.0 0.0; 0.0 1.0],
    sites = [(0.0, 0.0), (0.5, 0.5)],
    charges = [1.0, -1.0],
)

result = latticesum(square; tolerance = 1e-12)
result.converged      # true
```

If `result.converged` is `false` on this structure, something is wrong with the install
rather than with the structure — it is the easiest case there is.
