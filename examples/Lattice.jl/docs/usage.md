# Defining a structure

A `PeriodicStructure` is three fields and a handful of constraints. Getting them right
is most of the work of using the package.

## The three fields

```julia
using Lattice

structure = PeriodicStructure(
    cell = [1.0 0.0; 0.0 1.0],
    sites = [(0.0, 0.0), (0.5, 0.5)],
    charges = [1.0, -1.0],
)
```

| Field | Shape | Meaning |
| --- | --- | --- |
| `cell` | `d × d` matrix | the lattice vectors, as **columns** |
| `sites` | vector of `d`-tuples | fractional coordinates in `[0, 1)` |
| `charges` | vector of `Float64` | one weight per site |

`d` is 2 or 3. It is taken from `cell`, and `sites` must agree with it.

## The constraints

They are checked by the constructor, so a bad structure fails where it is written
rather than deep inside a sum:

- **`cell` must be non-singular.** A degenerate cell has no reciprocal lattice.
- **`charges` must sum to zero**, to within `sqrt(eps())`. A charged cell has no finite
  lattice sum; see [Lattice sums](lattice-sums.md#what-this-does-not-do).
- **`sites` must be in `[0, 1)`.** Coordinates outside it are a sign that Cartesian
  positions were passed by mistake, which would otherwise give a quietly wrong answer.
- **`sites` and `charges` must be the same length.**

```julia
PeriodicStructure(
    cell = [1.0 0.0; 0.0 1.0],
    sites = [(0.0, 0.0)],
    charges = [1.0],
)
# ArgumentError: charges sum to 1.0, not zero
```

## Cartesian positions

If you have Cartesian coordinates, convert them rather than passing them:

```julia
cartesian = [(0.0, 0.0), (1.4, 1.4)]
cell = [2.8 0.0; 0.0 2.8]
sites = [Tuple(cell \ [x, y]) for (x, y) in cartesian]
```

!!! note "The backslash, not the inverse"
    `cell \ v` solves rather than inverting, which matters for a cell with very
    different vector lengths. The package does the same internally.

## A three-dimensional example

```julia
fcc = PeriodicStructure(
    cell = [1.0 0.0 0.0; 0.0 1.0 0.0; 0.0 0.0 1.0],
    sites = [(0.0, 0.0, 0.0), (0.5, 0.5, 0.0),
             (0.5, 0.0, 0.5), (0.0, 0.5, 0.5),
             (0.5, 0.5, 0.5), (0.0, 0.0, 0.5),
             (0.0, 0.5, 0.0), (0.5, 0.0, 0.0)],
    charges = [1.0, 1.0, 1.0, 1.0, -1.0, -1.0, -1.0, -1.0],
)

latticesum(fcc; tolerance = 1e-12).converged
```

## Limitations

- Charges are scalars. There is no dipole or higher multipole.
- A structure is rigid once constructed. To move a site, build another structure; the
  constructor is cheap and the validation is worth re-running.
- Nothing here is thread-safe to mutate, because nothing here is mutable.
