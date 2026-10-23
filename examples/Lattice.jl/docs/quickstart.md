# Quickstart

One structure, one sum, and the certificate that comes with it.

## Install

[Installation](install.md) has the full set of requirements. From a clone:

```bash
git clone https://github.com/example/Lattice.jl
cd Lattice.jl
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

## Define a structure

```julia
using Lattice

structure = PeriodicStructure(
    cell = [1.0 0.0; 0.0 1.0],
    sites = [(0.0, 0.0), (0.5, 0.5)],
    charges = [1.0, -1.0],
)
```

`cell` holds the lattice vectors as columns, `sites` their fractional coordinates, and
`charges` one weight per site. [Defining a structure](usage.md) covers the constraints.

## Take the sum

```julia
result = latticesum(structure; splitting = 0.35, tolerance = 1e-10)
```

`result` is a `LatticeSum`. The three fields worth looking at first:

```julia
result.value      # the sum, excluding the self-term
result.bound      # an upper bound on everything truncated away
result.self       # the self-term, reported but not included
```

If `result.bound` is larger than the tolerance you asked for, the solver could not get
there within its shell limits and says so in `result.converged`. That is a result to
investigate, not to round.

## Choose the splitting

The `splitting` parameter decides how much of the work goes to each part. It changes
nothing about the answer and everything about the cost:

```julia
for s in (0.2, 0.35, 0.6)
    r = latticesum(structure; splitting = s, tolerance = 1e-10)
    println(s, "  ", r.shells, " shells, ", r.vectors, " vectors")
end
```

All three print the same `value` to the requested tolerance. See
[The convergence certificate](certificate.md#choosing-the-splitting) for how to pick
one without guessing.

## What to read next

- [Lattice sums](lattice-sums.md): what the splitting actually does.
- [Defining a structure](usage.md): the fields and their constraints.
- [API reference](api.md): the full surface.
