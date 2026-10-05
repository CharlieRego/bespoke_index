# Reading a model bill the way cost accounting reads materials

Standard costing exists because a single overspend is a poor teacher. "This batch cost $32 more than the recipe" is a fact. It does not say whether the grocer charged more, the baker used more, or the baker quietly swapped cheap flour for expensive butter. Material variances are a way of letting one cause move while the others stay still, so each dollar of the gap has a name.

The same gap shows up on a public AI leaderboard. A model can have the cheaper rate card and still send the larger bill, because it writes more, thinks longer, or spends its tokens on the expensive class. Artificial Analysis publishes the pieces of that sentence separately: prices, a frozen-mix blended price, cost per task, tokens per task, and a clock. The old names for those pieces are material price variance (MPV), material usage variance (MUV), and material mix variance (MMV), with usage split once more into mix and yield (MYV).

Figures below that name a live model are a snapshot from Artificial Analysis around late September 2026 (comparison pages and the methodology). Live numbers move. The arithmetic is the part worth keeping.

## What a variance is allowed to change

Take one unit of output. Call the recipe the standard, and the grocery receipt the actual.

- **SQ, SP**: standard quantity and standard price. The recipe.
- **AQ, AP**: actual quantity and actual price. The receipt.
- **RSQ**: revised standard quantity. The actual total amount of material, rearranged back into the recipe's proportions.

The total gap, the material cost variance, is the recipe cost of the output you got, minus the money you actually spent:

```
MCV = (SQ × SP) − (AQ × AP)
```

A positive result is favorable: the receipt came in under the recipe. A negative result is adverse. Textbooks also write the same idea as standard cost of actual output minus actual cost. One task, one batch, one loaf: the output is held still, and only the spending moves.

That total always splits into a price piece and a quantity piece:

```
MPV = AQ × (SP − AP)
MUV = (SQ − AQ) × SP
MCV = MPV + MUV
```

Each formula freezes one thing on purpose.

Price variance uses **actual** quantity. A discount on flour you never bought saves nothing, so the price gap is applied only to what was purchased. Usage variance uses **standard** price. If usage were also priced at the actual price, the price gap would be counted twice, once in each variance, and the two lines would no longer add back to the total. Standard price keeps the usage line as a pure quantity effect.

Usage itself has two different stories, and they are easy to tangle if they stay in one number. A baker can use more food in total. A baker can also use the same total weight and still spend more, by moving the weight onto butter. Mix holds the total weight at whatever was actually used, and asks only about proportions. Yield holds the proportions at the recipe, and asks only about scale.

```
RSQ of one ingredient = (total AQ) × (that ingredient's SQ / total SQ)

MMV = (RSQ − AQ) × SP
MYV = (SQ − RSQ) × SP
MUV = MMV + MYV
```

RSQ is the question: "If this batch had used the actual total kilograms, but still in the recipe's mix, how many kilograms of each ingredient would that have been?" Anything the actual mix does differently from that hypothetical is mix. Anything left between the original recipe and that hypothetical is yield.

The check, every time, is that the pieces return the total:

```
MPV + MMV + MYV = MCV
```

If they do not, some quantity has been counted twice or left out. On a model bill the usual way to break the check is to treat reasoning tokens as a fourth material when the provider already billed them inside output.

## A small batch, before any model names

One batch. Two ingredients. Standard recipe: 10 kg of flour at $2, and 2 kg of butter at $10. Recipe cost, $40.

The baker actually used 8 kg of flour at $3, and 6 kg of butter at $8. Receipt, $72. The batch cost $32 more than the recipe. Adverse MCV of $32.

| Ingredient | SQ | SP | AQ | AP | Recipe $ | Receipt $ |
|---|---:|---:|---:|---:|---:|---:|
| Flour | 10 kg | $2 | 8 kg | $3 | 20 | 24 |
| Butter | 2 kg | $10 | 6 kg | $8 | 20 | 48 |
| Total | 12 kg | | 14 kg | | 40 | 72 |

Price variance, on the kilograms actually bought:

- Flour: 8 × ($2 − $3) = $8 adverse. Flour was dearer.
- Butter: 6 × ($10 − $8) = $12 favorable. Butter was cheaper.
- MPV = $4 favorable.

The rate card, taken alone, was a small win. It is not the story of the batch.

Usage variance, at recipe prices:

- Flour: (10 − 8) × $2 = $4 favorable. Less flour than the recipe.
- Butter: (2 − 6) × $10 = $40 adverse. Four extra kilograms of the expensive ingredient.
- MUV = $36 adverse.

$4 favorable plus $36 adverse is the $32. The total is already explained. The next split says what kind of quantity problem it was.

Total weight went from 12 kg to 14 kg. The recipe is 10/12 flour and 2/12 butter. Spread the actual 14 kg across that mix:

- RSQ flour = 14 × 10/12 = 11.667 kg
- RSQ butter = 14 × 2/12 = 2.333 kg

Mix, the departure from those proportions, at recipe prices:

- Flour: (11.667 − 8) × $2 = $7.33 favorable. The batch was light on flour.
- Butter: (2.333 − 6) × $10 = $36.67 adverse. The batch was heavy on butter.
- MMV = $29.33 adverse.

Yield, the scale change after proportions are restored:

- Flour: (10 − 11.667) × $2 = $3.33 adverse
- Butter: (2 − 2.333) × $10 = $3.33 adverse
- MYV = $6.67 adverse

Mix $29.33 adverse plus yield $6.67 adverse is the $36 usage variance. The batch is overweight by a little. It is butter-heavy by a lot. A buyer who only renegotiates the flour price will not touch the cause.

That is the whole method. Three materials instead of two does not change it. A token bill is this batch.

## The same batch, made of tokens

One completed task is the batch. For Artificial Analysis, the natural batch is one task in the Intelligence Index: a fixed body of work, scored, timed, and costed the same way across models.

The ingredients are the classes a provider bills at different prices:

| Ingredient in the bakery | Token class | Why it has its own price |
|---|---|---|
| Flour, the cheap bulk | Cache-hit input | The provider replays context it already stored, at a large discount |
| The mid-price ingredient | Fresh input | Prompt tokens that miss the cache |
| Butter, the expensive one | Output, including reasoning | Generated tokens. Reasoning is usually billed as output, so it belongs on this line |

A model does not choose a rate card in isolation. It also chooses, by how it behaves, how many tokens of each class the task eats. Agentic work multiplies input, because a long trajectory re-sends context on every turn. Reasoning multiplies output, because thinking tokens are paid for on the way to a short answer. Cache-hit rate decides how much of the re-sent context gets the flour price instead of the fresh-input price.

So a higher cost per task can be a dearer price, a longer trajectory, a more verbose answer, a shift from cache hits onto output, or any mix of those. The variances separate them. The leaderboard's single "cost" column sums them.

## What the public numbers already are

Artificial Analysis, in its methodology, defines the pieces in costing language even though it uses its own names.

**Input price, output price, cache-hit price.** These are AP or SP, depending on which model you treat as the recipe. They are dollars per million tokens on the provider's card.

**Blended price.** A standard-mix price index. The published blend assumes 7 cache-hit : 2 fresh input : 1 output. Every model is priced as if it ate that recipe. Opus 5.5 (max) blended to $2.94 per million tokens because `0.7 × 0.20 + 0.2 × 4 + 0.1 × 20 = 2.94`. Astra (max) blended to $7.70 because `0.7 × 1 + 0.2 × 10 + 0.1 × 50 = 7.70`. Comparing those two numbers is a comparison of rate cards on a frozen agent-shaped mix. Quantity never enters. Actual mix never enters. A blended-price ranking is the closest public cousin of "whose price list is cheaper," and it is silent on the receipt.

**Cost per task.** The receipt for one Intelligence Index task. Token prices multiplied by tokens actually consumed, with each benchmark weighted the way the Intelligence Index weights it. Their own gloss is the usage variance in one line: models that produce longer answers or more reasoning tokens cost more per task even at identical per-token prices.

**Output tokens per task, and reasoning tokens per task.** AQ for the expensive class, and the part of that class that was thinking. Reasoning stays inside output for the variance so the bill still foots. It is then the right place to look when the output line of the usage variance is the large one.

**Intelligence Index.** The grade of the batch. Variances compare like with like. A higher score is a richer product, discussed with the scorecard rather than pushed into MPV.

**Output speed and time to first token.** A second experiment. The performance benchmark sends its own prompts and counts **OpenAI tokens**, so the same text is the same number of tokens on every model. The Intelligence Index bill uses each provider's **native tokens**, because those are the units on the invoice. A native token and an OpenAI token are different rulers. They support different sentences. Adding them, or dividing index tokens by benchmark tokens per second, produces a time that neither experiment measured.

Around that snapshot, the headline that makes the method worth learning:

| | Opus 5.5 (max) | GPT-6 Astra (max) | Gemini 4 Argon (high) |
|---|---:|---:|---:|
| Intelligence Index | 58 | 53 | 53 |
| Blended $/1M | 2.94 | 7.70 | 1.47 |
| Cost per task | $5.98 | $3.26 | $1.99 |
| Output tokens per task | 119k | 27k | 62k |

Astra's rate card is much dearer than Opus's, and Astra's task is cheaper. Output tokens are the visible reason: 27k against 119k. Gemini and Astra sit on the same index score, 53, so the gap between $1.99 and $3.26 is a spending difference on the same grade of product. Opus at 58 also bought five index points; those points are real output, and they sit beside the cost variance.

## Reading one receipt in full

The free comparison page publishes output tokens and the three prices. It folds cache-hit and fresh-input quantities into cost per task. A full three-way split needs those two quantities as well. The table below keeps the published output counts and the published Opus and Astra prices, and fills cache and fresh input with round teaching quantities. Swap in measured counts and the same lines apply. With these fills, the teaching receipt is $2.35 standard against $3.05 actual, which is the shape of the real gap (Astra cheaper per task despite the dearer card) at a smaller dollar level than the live $3.26 against $5.98.

The recipe is Astra's card and Astra's frugal quantities. The receipt is Opus's card and Opus's larger quantities.

| Class | SQ | SP $/1M | AQ | AP $/1M | Recipe $ | Receipt $ |
|---|---:|---:|---:|---:|---:|---:|
| Cache hit | 200,000 | 1.00 | 350,000 | 0.20 | 0.20 | 0.07 |
| Fresh input | 80,000 | 10.00 | 150,000 | 4.00 | 0.80 | 0.60 |
| Output | 27,000 | 50.00 | 119,000 | 20.00 | 1.35 | 2.38 |
| Total | 307,000 | | 619,000 | | 2.35 | 3.05 |

MCV = $2.35 − $3.05 = **$0.70 adverse**. Seventy cents more than the recipe, per task.

**Price, $4.75 favorable.** On the tokens actually used, Opus's card is cheaper in every class:

- Cache: 350,000 × ($1.00 − $0.20) / 1,000,000 = $0.28
- Fresh input: 150,000 × ($10 − $4) / 1,000,000 = $0.90
- Output: 119,000 × ($50 − $20) / 1,000,000 = $3.57

Someone who stopped at the rate card would expect a large saving. The saving is real. It is smaller than the quantity effect that comes with it.

**Usage, $5.45 adverse**, at Astra's prices:

- Cache: (200,000 − 350,000) × $1 / 1,000,000 = $0.15 adverse
- Fresh input: (80,000 − 150,000) × $10 / 1,000,000 = $0.70 adverse
- Output: (27,000 − 119,000) × $50 / 1,000,000 = $4.60 adverse

Output is about five-sixths of the usage variance. The extra thinking and the extra answer, priced as if they had been bought on the expensive card, cost more than the entire rate-card saving.

Now the split of that $5.45. Total tokens went from 307,000 to 619,000, almost exactly double. The recipe's mix is 200/307 cache, 80/307 fresh input, 27/307 output. Spread the actual 619,000 tokens across that mix and you get RSQ of about 403,257 cache, 161,303 fresh input, and 54,440 output.

**Mix, $3.06 adverse.** Actual output was 119,000 tokens against an RSQ of 54,440. That surplus of output, and the matching deficit of cache and fresh input, priced at standard:

- Cache and fresh input together, about $0.17 favorable (the mix was light on the cheaper classes)
- Output, about $3.23 adverse

Output's share of all tokens moved from about 9% in the recipe to about 19% on the receipt. Mix is that shift, and little else.

**Yield, $2.39 adverse.** Even after the mix is restored, every class is scaled up by about the same doubling. At standard prices that scale costs $2.39. Yield here means "more tokens for the same task," which is the everyday meaning of token inefficiency once the mix has been given its own line.

Check: $4.75 favorable, plus $3.06 adverse, plus $2.39 adverse, equals $0.70 adverse.

Read as a manager, the seventy cents is a bad guide to action. The rate card is already the favorable part. Renegotiating it further is work on the $4.75, which has been banked. The open problem is the output line: a mix shift into generated tokens, plus a general increase in how long the trajectory is. Effort setting, verbosity, retry behavior, and how much of the context is cacheable are the levers that move MMV and MYV. Provider choice is the lever that moves MPV.

## When the rate card does not move, the whole gap is usage

The cleanest public illustration needs no assumed quantities. Anthropic priced Claude Sonnet 5.5 at the same $0.20 / $2 / $10 per million cache-hit, input, and output tokens as Sonnet 5. Artificial Analysis still measured about $7.60 per Intelligence Index task, on the order of 50% higher than Sonnet 5, with about 193,000 output tokens per task at max effort.

Identical prices mean AP equals SP on every class, so MPV is zero on every class. Whatever the cost per task did, usage did. If those extra tokens are mostly output and reasoning, the usage line will itself be mostly mix: the same sort of shift the butter made, from cheaper context onto generated tokens. If the whole trajectory scaled up in proportion, more of the line will be yield. Publishing the three quantities would settle which. The price line is already settled.

Effort level belongs in this paragraph. Low, medium, high, and max are process settings. They change how much the model writes and thinks. Comparing max with low on purpose produces a large usage variance, the way comparing a rich dough with a lean dough produces a large butter variance. That variance describes the setting. It does not, by itself, say the model is wasteful. Hold effort still when the question is "which model," and let effort vary when the question is "what does this dial cost."

## Time is a second ledger

The material identity is exhausted by tokens and prices. Minutes do not appear in it. The tokens that occupied those minutes are already in AQ, and therefore already in the bill. Putting the minutes into MCV as well would count the same generation twice.

Minutes get their own variance when a minute has a price of its own: a person waiting, an SLA, a reserved machine. That is the shape of a labor efficiency variance. Standard minutes allowed for the work, minus actual minutes, times the price of a minute. Favorable when the work finishes inside the allowance.

On one measured run the clock has an identity as tight as the cost identity. Time to first token, then the output tokens divided by the speed after that first token:

```
T = TTFT + (output tokens / speed)
```

The difference between two runs on that same clock splits into three named pieces:

```
ΔT = (TTFT actual − TTFT standard)
   + (AQ − SQ) / standard speed
   + AQ × (1 / actual speed − 1 / standard speed)
```

Latency, token volume at the standard speed, and the speed change on the tokens actually generated. They add back to the difference in wall time.

A single-clock sketch, not an Artificial Analysis column-add:

| | TTFT | Output tokens | Speed | Time |
|---|---:|---:|---:|---:|
| Standard run | 2 s | 1,000 | 50 /s | 2 + 20 = 22 s |
| Actual run | 3 s | 4,000 | 80 /s | 3 + 50 = 53 s |

The actual run took 31 seconds longer. One second of that is a slower start. Sixty seconds is the extra 3,000 tokens at the standard 50 per second. Thirty seconds come back because 80 per second is faster than 50, applied to the 4,000 tokens actually written: `4,000 × (1/80 − 1/50) = −30`. `1 + 60 − 30 = 31`. The model was quicker per token and still much slower on the task, because it wrote four times as much. Same moral as the butter, on the clock.

Artificial Analysis's published Time per Task is the right total for the index workload. In the same snapshot, Opus (max) took about 828 seconds per task and Astra (max) about 528: five extra minutes. Those minutes are an operating fact. They are not a fourth material variance.

The speed pair published beside them, on the order of 90 tokens per second against 51, answers a different question. On a fixed 100 output tokens, `100/51 − 100/90` is under a second. Decode speed moves short answers. It does not account for a five-minute gap on tasks that emit tens of thousands of tokens and spend a long time thinking. Read Time per Task from the index. Read speed from the performance benchmark. Combine them only after both have been put on one ruler.

## The grade of the product stays outside the variance

A flour-and-butter variance is about one batch of one bread. A favorable usage variance on a batch that was thrown away is not a saving; the output the recipe was written for never arrived. Defective yield is a separate report.

Intelligence Index is that report. Astra (max) and Gemini 4 Argon (high) both sat at 53, so a cost variance between them is about the same grade of answer. Opus (max) at 58 against Astra at 53 spent more and also scored higher. The extra index points are closer to a different specification than to waste. One honest presentation is the variance inside a narrow band of index scores, with the score printed on the row. Another is to keep the dollar variance, and next to it the index points gained or given up, without forcing those points through the MPV formula. Cost per index point is a useful ratio. It is not a variance, and it will not foot to MCV, because index points are not linear in tokens and were never in the recipe as a quantity.

A cheaper endpoint for the same weights is, by contrast, a clean price question. MPV is the whole of it, provided the endpoint still delivers the product. Artificial Analysis's Endpoint Accuracy Index is the quality check on that claim: same evaluation, another host, sometimes a loss of score to quantization or serving choices. A favorable price variance with a fallen index is the cheap flour that did not bake.

## What each result is asking you to believe

After the lines foot, each one is a belief about cause.

- A large favorable **MPV** says the card you actually paid was kinder than the recipe's card, on the tokens this task really used. Provider, contract, and cache-discount design live here.
- A large adverse **MMV** says the task spent a greater share of its tokens on a dearer class than the recipe does. For these three classes, that almost always means more of the task became generation: longer answers, more reasoning, fewer cache hits relative to output. Prompt shape, effort, and caching live here.
- A large adverse **MYV** says the task used more tokens even after you give it the recipe's mix back. Longer trajectories, more turns, retries, and a generally more expansive model live here.
- A **zero MPV** next to a moved cost per task says the card is innocent. Sonnet 5.5 against Sonnet 5 is that pattern.
- A faster **speed** next to a worse **time per task** says volume owns the clock. The single-clock split shows how much.

The bakery test still works as a last reading. If the only action suggested by a line is "stare at the total," the line is not yet a variance. If the action is "the butter moved," it is.
