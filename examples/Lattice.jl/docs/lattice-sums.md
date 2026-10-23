# Lattice sums

## The problem

A lattice sum adds one term for every image of every site in a periodic structure. The
terms fall off slowly, so truncating at a radius leaves a tail that is both large and
hard to describe:

<div class="ds-math" markdown>
S = Σ<sub>n</sub> Σ<sub>j</sub> q<sub>j</sub> / |r + R<sub>n</sub> − r<sub>j</sub>|
<span class="ds-where">summed over all lattice translations R<sub>n</sub> and all sites j, excluding the term where the image coincides with the reference site</span>
</div>

Doubling the cut-off radius multiplies the work by eight in three dimensions and buys
one more digit. That trade is why the sum is split instead.

## The splitting

Each term is written as a short-range piece plus a long-range piece, with a parameter α
deciding where the handover happens:

<div class="ds-math" markdown>
1/r = erfc(αr)/r + erf(αr)/r
<span class="ds-where">the first term decays like a Gaussian and is summed in real space; the second is smooth and is summed over reciprocal vectors</span>
</div>

Neither piece is slowly convergent. The real-space part needs a few shells because
`erfc` kills it; the reciprocal part needs a few vectors because the transform of a
smooth function is compact. The exact answer is independent of α — only the cost
depends on it.

## The self-term

The sum excludes the term where an image coincides with the reference site, because
that term is infinite. The splitting, however, does not: the reciprocal-space part
quietly includes it, so it has to be subtracted back out.

`Lattice.jl` does that subtraction and then reports the quantity separately:

```julia
result = latticesum(structure; splitting = 0.35)
result.value      # the sum, self-term excluded
result.self       # the self-term that was subtracted
```

!!! info "Why it is reported rather than hidden"
    Different conventions fold the self-term into different places, and a value that
    silently includes or excludes it is impossible to compare against a published
    number. Reporting both means a reader can match whichever convention they have.

## The two parts, separately

```julia
result.real_part          # the erfc sum over lattice shells
result.reciprocal_part    # the erf sum over reciprocal vectors
result.shells             # shells the real-space part used
result.vectors            # reciprocal vectors the other part used
```

These are exposed for diagnosis, not for use. Their individual values depend on α and
mean nothing on their own; only the total is a physical quantity.

## What this does not do

- It does not compute forces or any derivative of the sum.
- It does not handle a structure with a net charge. `PeriodicStructure` requires the
  charges to sum to zero, because a charged periodic cell has no finite sum to compute
  and the reciprocal part's zero vector diverges.
- It does not treat a one-dimensional chain. See the scope note on the
  [home page](index.md#scope).
