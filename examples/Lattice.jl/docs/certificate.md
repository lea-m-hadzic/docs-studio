# The convergence certificate

## What `bound` is

`result.bound` is an upper bound on the absolute error of `result.value` from
truncation — nothing else. It is the sum of two bounds:

<div class="ds-math" markdown>
bound = B<sub>real</sub>(α, R) + B<sub>recip</sub>(α, G)
<span class="ds-where">where R is the real-space cut-off radius and G the reciprocal cut-off; each bound is the tail of a decaying series, summed in closed form</span>
</div>

Both tails are monotone in their cut-off, so the solver can raise a cut-off until its
bound is small enough rather than sampling and guessing.

## What it covers, and what it does not

| Source of error | In `bound`? |
| --- | --- |
| terms beyond the real-space cut-off | yes |
| reciprocal vectors beyond the cut-off | yes |
| the self-term subtraction | yes — it is exact, and contributes zero |
| floating-point accumulation | **no** |
| the structure being wrong | **no** |

!!! warning "Rounding is not in the bound"
    `bound` is a mathematical truncation bound. Accumulated floating-point error in
    `Float64` is separate, and on a large structure it sets a floor of roughly
    `eps() * n` that no tolerance can get under. Asking for `tolerance = 1e-18` does
    not fail loudly; it returns `converged = false`, because the solver ran out of
    shells before the bound got there.

## Reading the result

```julia
result = latticesum(structure; tolerance = 1e-10)

if !result.converged
    @warn "bound $(result.bound) did not reach the tolerance" result.shells result.vectors
end
```

`converged` is `result.bound <= tolerance`, and nothing more. A `false` means one of
three things: the tolerance is below the floating-point floor, the shell limit was
reached, or the splitting is badly chosen for this structure.

## Choosing the splitting

The cost of the two parts moves in opposite directions as α changes, so there is a
minimum. For a structure with N sites in a cell of volume V, balancing the two gives:

<div class="ds-math" markdown>
α ≈ (N π<sup>3</sup> / V<sup>2</sup>)<sup>1/6</sup>
<span class="ds-where">the standard balance for equal work in the two parts; it is a starting point, not an optimum for any particular machine</span>
</div>

```julia
balanced(structure)        # the α above, for this structure
```

Leaving `splitting` out uses `balanced(structure)`. Setting it by hand is worth doing
only when you are timing something, and it never changes the answer beyond the
tolerance you asked for:

```julia
a = latticesum(structure; splitting = 0.2,  tolerance = 1e-12)
b = latticesum(structure; splitting = 0.6,  tolerance = 1e-12)
abs(a.value - b.value) < 1e-12 + a.bound + b.bound     # true
```

That inequality is the certificate doing its job: two very different computations
agreeing to within the error each one claimed.
