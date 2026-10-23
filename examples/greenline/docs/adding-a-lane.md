# Adding a lane

The lane map is the project. Adding to it is the most useful thing a volunteer can do,
and it is also the easiest to get subtly wrong, so this page is specific.

## What counts as protected

A lane is **protected** when a person on a bike is physically separated from moving
motor traffic. Concretely:

| Separation | Protected? |
| --- | --- |
| kerb, planter, or bollards | yes |
| its own path, away from the road | yes |
| a parking lane between bike and traffic | yes |
| wand posts, flexible plastic | yes — but note it in the survey |
| painted stripe, any width or colour | **no** |
| shared bus lane | **no** |
| advisory lane with a dashed line | **no** |
| a quiet street with no lane at all | **no** |

!!! info "The cases that were argued about"
    Wand posts count, grudgingly: they are separation that a car can drive through, but
    they change driver behaviour enough that the volunteers voted to include them. A
    parking lane counts only where parking is permitted all day — a lane that becomes a
    traffic lane at rush hour is not separation.

## Survey a segment

Walk or ride it, end to end, and record:

1. the two endpoints, as coordinates
2. the separation type, from the table above
3. the surface: `asphalt`, `concrete`, `gravel`, `cobbles`
4. the usable width, at the narrowest point, in centimetres
5. anything a rider would want warning about

Narrowest point, not average. A lane that is two metres wide except for the 80 cm
pinch at the bridge is an 80 cm lane for anyone with a trailer.

## Add it to the map

```bash
greenline lanes add survey.json
```

```json
{
  "name": "Mill Street bike lane",
  "from": [51.5072, -0.1276],
  "to": [51.5094, -0.1251],
  "separation": "bollards",
  "surface": "asphalt",
  "width_cm": 180,
  "notes": "Narrows to 180 cm at the Mill Street junction."
}
```

The command validates the file, checks the endpoints land inside the city bounds, and
opens a pull request against the map repository. A second volunteer reviews it; that is
not a formality, and about one in five surveys comes back with a question.

## What not to add

- A lane you have not been on. Aerial imagery is not a survey.
- A lane that is planned but not built, however certain the plan looks.
- A lane outside the city bounds, even a good one.
- Anything from another map's data, unless its licence allows it and you say where it
  came from. See [House style](house-style.md#attribution).
