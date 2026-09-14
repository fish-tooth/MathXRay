# Baseline Diagnosis (human verification checklist)

- Source: `results\raw\B0-DirectJudge_pilot.jsonl`, `results\raw\B0-DirectJudge_dev.jsonl`
  (latest record per sample_id). Agreement/disagreement counts below;
  every non-agree sample is listed for manual review before Gate G1.

## Summary
| Category | n |
|---|---|
| AGREE | 278 |
| MISS | 2 |
| FALSE_ALARM | 14 |
| LOCALIZE_OFF | 47 |
| PARSE_FAIL | 8 |
| API_FAIL | 0 |

Samples requiring verification (non-AGREE, excluding API_FAIL): **71**.

## Per-source
| Source | AGREE | MISS | FALSE_ALARM | LOCALIZE_OFF | PARSE_FAIL | API_FAIL |
|---|---|---|---|---|---|---|
| gsm8k | 33 | 0 | 0 | 3 | 0 | 0 |
| math | 86 | 0 | 5 | 12 | 0 | 0 |
| olympiadbench | 80 | 0 | 4 | 15 | 6 | 0 |
| omnimath | 79 | 2 | 5 | 17 | 2 | 0 |

## MISS — gold invalid, judge said correct (2)

Costliest error: missed a real process error.

### `omnimath-780` (omnimath)

- gold: process_correct=False first_error=3 A_correct=True
- pred: process_correct=True first_error=None type=None parse=SUCCESS
- reason: All steps are valid: cyclic symmetry and vanishing on equal variables imply factor (x-y)(y-z)(z-x) times linear cyclic factor x+y+z; constants computed correctly.
- problem: Suppose that $P(x, y, z)$ is a homogeneous degree 4 polynomial in three variables such that $P(a, b, c)=P(b, c, a)$ and $P(a, a, b)=0$ for all real $a, b$, and $c$. If $P(1,2,3)=1$, compute $P(2,4,8)$.

### `omnimath-543` (omnimath)

- gold: process_correct=False first_error=1 A_correct=True
- pred: process_correct=True first_error=None type=None parse=SUCCESS
- reason: Step 1 correctly identifies the number as 1001^7 via its digit blocks; steps 3-4 correctly factor 1001=7*11*13 and apply exponent rules, yielding a valid prime factorization.
- problem: Compute the prime factorization of 1007021035035021007001.

## FALSE_ALARM — judge said invalid, gold says correct (14)

### `math-558` (math)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=3 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 3 incorrectly claims 5π/3 is between π/2 and π and that sine is negative in that interval; this is a trigonometric concept error, though the final y value is correct.
- problem: Convert the point $\left( 6 \sqrt{3}, \frac{5 \pi}{3}, -2 \right)$ in cylindrical coordinates to rectangular coordinates.

### `math-944` (math)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=1 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 1 falsely claims 3a^2+19a+30 cannot be factored, but it factors as (a+3)(3a+10).
- problem: If $a$ is a positive integer, then $3a^2+19a+30$ and $a^2+6a+9$ are also positive integers. We define the function $f$ such that $f(a)$ is the greatest common divisor of  $3a^2+19a+30$ and $a^2+6a+9$.  Find the maximum possible value of $f(a)- a$.

### `math-882` (math)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=4 type=LOGIC_GAP parse=SUCCESS
- reason: Step 4 erroneously derives 513 as third-largest (already listed) before correcting, showing invalid ordering logic.
- problem: The digits 1, 3 and 5 are each used once to form each of the possible three-digit positive integers. The three-digit integers are listed from greatest to least. Which integer is listed fifth?

### `math-988` (math)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=3 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 3 incorrectly claims conjugate eliminates radical via addition or subtraction; conjugates rationalize via multiplication, and subtraction does not eliminate the radical.
- problem: What is the radical conjugate of $5 - 6\sqrt{2}$?

### `math-786` (math)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=1 type=THEOREM_MISUSE parse=SUCCESS
- reason: Step 1 incorrectly cites the conjugate root theorem to claim -√(1+√6) is the conjugate of √(1+√6); the theorem does not make the additive inverse a conjugate for real algebraic numbers.
- problem: There is a unique polynomial $P(x)$ of degree $4$ with rational coefficients and leading coefficient $1$ which has $\sqrt{1+\sqrt{6}}$ as a root. What is $P(1)$?

### `olympiadbench-897` (olympiadbench)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=4 type=ARITHMETIC_ERROR parse=SUCCESS
- reason: Step 4 incorrectly states 6084 * 6084 = 36,997,536; the correct product is 37,015,056, making the subsequent division equality invalid.
- problem: In a game, a player chooses 2 of the 13 letters from the first half of the alphabet (i.e., A-M) and 2 of the 13 letters from the second half of the alphabet (i.e., N-Z). Aditya plays the game, and then Ayesha plays the game. Compute the probability that Aditya and Ayesha choose …

### `olympiadbench-936` (olympiadbench)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=7 type=LOGIC_GAP parse=SUCCESS
- reason: Step 7 concludes the time is minimal, but no lower bound (e.g., t >= n/2) was proven; only a working strategy of length n/2 was given.
- problem: Elizabeth is in an "escape room" puzzle. She is in a room with one door which is locked at the start of the puzzle. The room contains $n$ light switches, each of which is initially off. Each minute, she must flip exactly $k$ different light switches (to "flip" a switch means to …

### `olympiadbench-610` (olympiadbench)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=1 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 1 erroneously assumes the arithmetic progression must end exactly at 999, but the problem only bounds answers within 000-999 inclusive.
- problem: The Local Area Inspirational Math Exam comprises 15 questions. All answers are integers ranging from 000 to 999, inclusive. If the 15 answers form an arithmetic progression with the largest possible difference, compute the largest possible sum of those 15 answers.

### `olympiadbench-541` (olympiadbench)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=1 type=THEOREM_MISUSE parse=SUCCESS
- reason: Step 1 cites the logarithm property log_a b^c = c log_a b to justify rewriting (sqrt{x})^{log10 x} as x^{(1/2)log10 x}, but that rewrite relies on the exponent power rule (a^b)^c = a^{bc}, not the cited log property.
- problem: Determine all values of $x$ for which $(\sqrt{x})^{\log _{10} x}=100$.

### `omnimath-640` (omnimath)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=4 type=HALLUCINATION parse=SUCCESS
- reason: Step 4 incorrectly includes 1024 in the divisor list of 1536; 1024 is not a divisor since 1536 = 2^9 * 3.
- problem: Find the largest integer less than 2012 all of whose divisors have at most two 1's in their binary representations.

### `omnimath-940` (omnimath)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=9 type=LOGIC_GAP parse=SUCCESS
- reason: Step 9 asserts f(x)=x+1 as the final answer without providing any derivation or logical support from the preceding steps.
- problem: Find all functions $ f : \mathbb{R} \rightarrow \mathbb{R} $ such that \[ f( xf(x) + 2y) = f(x^2)+f(y)+x+y-1 \] holds for all $ x, y \in \mathbb{R}$.

### `omnimath-835` (omnimath)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=4 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 4 incorrectly maps the clockwise 90° rotation of the top-left quadrant: position 2 (top-right) should map to 6 (bottom-right), not 5 (bottom-left).
- problem: Sixteen wooden Cs are placed in a 4-by-4 grid, all with the same orientation, and each is to be colored either red or blue. A quadrant operation on the grid consists of choosing one of the four two-by-two subgrids of Cs found at the corners of the grid and moving each C in the s…

### `omnimath-562` (omnimath)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=2 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 2 erroneously claims triangles PMA and PMQ are right triangles; P, M, Q are collinear on PQ, so PMQ is degenerate, not a triangle. The correct right triangles are PMA and QMA.
- problem: Points $P$ and $Q$ are 3 units apart. A circle centered at $P$ with a radius of $\sqrt{3}$ units intersects a circle centered at $Q$ with a radius of 3 units at points $A$ and $B$. Find the area of quadrilateral APBQ.

### `omnimath-730` (omnimath)

- gold: process_correct=True first_error=None A_correct=True
- pred: process_correct=False first_error=2 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 2 erroneously assumes maximizing each factor (a-b) and (c-d) independently yields the maximal product, ignoring the trade-off required by distinctness; the greedy choice gives 63 but (10-2)(9-1)=64 is larger.
- problem: Four distinct integers $a, b, c$, and $d$ are chosen from the set $\{1,2,3,4,5,6,7,8,9,10\}$. What is the greatest possible value of $ac+bd-ad-bc$?

## LOCALIZE_OFF — both invalid, first-error step differs (47)

### `gsm8k-140` (gsm8k)

- gold: process_correct=False first_error=4 A_correct=False
- pred: process_correct=False first_error=1 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 1 plans to add the deposit to the cost, but the deposit is already paid and should be subtracted from the total owed.
- problem: George needs to pay for dental work. He needs 2 implants. Each implant has a base price of $2000. For one of the implants, he wants a crown made of porcelain. That feature costs an extra $500. He’s already put down a deposit of $600. He makes $15 per hour at work. How many hours…

### `math-89` (math)

- gold: process_correct=False first_error=15 A_correct=False
- pred: process_correct=False first_error=8 type=ALGEBRA_ERROR parse=SUCCESS
- reason: Step 8 incorrectly equates (x^2+cx+d)^2 to x^4+ax^3+x^2+bx+1, but the polynomial from Step 3 is x^4+ax^3+bx+1 (the x^2 term canceled). The x^2 coefficient should be 0, not 1.
- problem: The parabola $y = x^2$ is tangent to the graph of $y = x^4 + ax^3 + x^2 + bx + 1$ at two points.  Find the positive difference between the $x$-coordinates of the points of tangency.

### `math-432` (math)

- gold: process_correct=False first_error=4 A_correct=False
- pred: process_correct=False first_error=1 type=LOGIC_GAP parse=SUCCESS
- reason: Step 1 lists the same condition twice as two distinct cases (three 1s and one prime vs one prime and three 1s), leading to double counting and an incorrect favorable count of 24 instead of 12.
- problem: Four standard six-sided dice are to be rolled. What is the probability that the product of the numbers on the top faces will be prime? Express your answer as a common fraction.

### `math-32` (math)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=1 type=THEOREM_MISUSE parse=SUCCESS
- reason: Step 1 incorrectly claims the infinite geometric series formula applies to this finite sum (terms only up to 1/2^10), misusing the theorem.
- problem: What is the following value when expressed as a common fraction: $$\frac{1}{2^{1}}+\frac{1}{2^{2}}+\frac{1}{2^{3}}+\cdots + \frac{1}{2^{8}}+\frac{1}{2^{9}}+\frac{1}{2^{10}}?$$

### `math-30` (math)

- gold: process_correct=False first_error=6 A_correct=False
- pred: process_correct=False first_error=1 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 1 states roots are exp(2kπi/2017) for k=0..2016, which includes 1 (not a root), contradicting the earlier correct claim that roots exclude 1.
- problem: Let $x_1,$ $x_2,$ $\dots,$ $x_{2016}$ be the roots of \[x^{2016} + x^{2015} + \dots + x + 1 = 0.\]Find \[\frac{1}{(1 - x_1)^2} + \frac{1}{(1 - x_2)^2} + \dots + \frac{1}{(1 - x_{2016})^2}.\]

### `omnimath-159` (omnimath)

- gold: process_correct=False first_error=2 A_correct=False
- pred: process_correct=False first_error=1 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 1 wrongly states that chords AX and BY intersect at C and that C is outside; the problem says lines AB and XY intersect at C, so the theorem application is misread.
- problem: Let $A X B Y$ be a cyclic quadrilateral, and let line $A B$ and line $X Y$ intersect at $C$. Suppose $A X \cdot A Y=6, B X \cdot B Y=5$, and $C X \cdot C Y=4$. Compute $A B^{2}$.

### `omnimath-980` (omnimath)

- gold: process_correct=False first_error=3 A_correct=True
- pred: process_correct=False first_error=1 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 1 incorrectly assumes d=gcd(a,b) divides c, writing c=dz, which is not generally true.
- problem: Given that $a, b, c$ are positive integers satisfying $$a+b+c=\operatorname{gcd}(a, b)+\operatorname{gcd}(b, c)+\operatorname{gcd}(c, a)+120$$ determine the maximum possible value of $a$.

### `omnimath-389` (omnimath)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=1 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 1 misstates the definition: 'bettered by' should mean the other triple has exactly two coordinates larger, i.e., b_i > a_i, not a_i > b_i.
- problem: We say a triple of real numbers $ (a_1,a_2,a_3)$ is [b]better[/b] than another triple $ (b_1,b_2,b_3)$ when exactly two out of the three following inequalities hold: $ a_1 > b_1$, $ a_2 > b_2$, $ a_3 > b_3$. We call a triple of real numbers [b]special[/b] when they are nonnegati…

### `gsm8k-15` (gsm8k)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=2 type=ARITHMETIC_ERROR parse=SUCCESS
- reason: Step 2 states '1st - 5 = 6th', which is mathematically false (1-5=-4). Although the resulting place is correct, the equation itself is invalid arithmetic.
- problem: Finley took part in a 100-meter race.  She started off in first, but then fell back 5 spots.  She then moved ahead 2 spots, before falling behind 3.  Lastly, she jumped ahead 1 spot to finish the race.  What place did she finish in?

### `gsm8k-81` (gsm8k)

- gold: process_correct=False first_error=5 A_correct=False
- pred: process_correct=False first_error=3 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 3 states the class extension probability as 40% unconditionally, omitting the condition that the normal teacher must be present (only 50% of the time).
- problem: Marcus is trying to decide whether he really needs to do his homework. There's a 50% chance that tomorrow he'll have a substitute teacher who won't collect the homework. Even if the normal teacher comes in, there's a 40% chance she'll give everyone an extension. Even if the whol…

### `math-389` (math)

- gold: process_correct=False first_error=2 A_correct=False
- pred: process_correct=False first_error=1 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 1 misreads the diagram: the 5x-8° label is at B (not ∠BAC) and 143° is at D, not an angle of triangle ABC.
- problem: Lines $l$ and $m$ are parallel and points $A$, $B$, and $D$ are collinear. What is the value of $x$?  [asy]  unitsize(1.1 inch);  draw((0,0)--(4,0),Arrows);  draw((0,1)--(4,1),Arrows);  draw((3,2)--(1,-1),Arrows);  dot((0.3,0)); label("$m$",(0.3,0),N);  dot((0.3,1)); label("$l$"…

### `math-618` (math)

- gold: process_correct=False first_error=6 A_correct=True
- pred: process_correct=False first_error=1 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 1 incorrectly interprets the side length labels 30 (on BX) and 45 (on BC) as angle measures; they are side lengths, not angles.
- problem: Find $AX$ in the diagram if $CX$ bisects $\angle ACB$. [asy] import markers;  real t=1-.32; pair A=(-4.07,0); pair B=(40.008,0); pair C=(0,20.616); pair X=t*A+(1-t)*B;  draw(C--A--B--C--X);  label("$A$",A,SW); label("$B$",B,E); label("$C$",C,N); label("$X$",X,S);  //markangle(n=…

### `math-80` (math)

- gold: process_correct=False first_error=1 A_correct=False
- pred: process_correct=False first_error=2 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 2 misreads diagram: 8 is the hypotenuse of the 30-60-90 triangle, not the side opposite 30°, and x is not the side opposite 60°.
- problem: What is the value of $x$ in the diagram?  [asy] import olympiad; draw((0,0)--(sqrt(3),0)--(0,sqrt(3))--cycle); draw((0,0)--(-3,0)--(0,sqrt(3))--cycle); label("8",(-3/2,sqrt(3)/2),NW); label("$x$",(sqrt(3)/2,sqrt(3)/2),NE); draw("$45^{\circ}$",(1.5,0),NW); draw("$30^{\circ}$",(-2…

### `math-721` (math)

- gold: process_correct=False first_error=5 A_correct=True
- pred: process_correct=False first_error=2 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 2 drops the left part of the original two-sided inequality (-4 < ...) and only keeps the upper bound, without justification.
- problem: For what real values of $x$ is $-4<x^{4}+4x^{2}<21$ satisfied? Express your answer in interval notation.

### `math-791` (math)

- gold: process_correct=False first_error=4 A_correct=True
- pred: process_correct=False first_error=2 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 2 gives domain as sin x > 0, omitting the square root condition log_2(sin x) >= 0, which restricts domain to sin x = 1.
- problem: Find the number of integers in the range of the real-valued function $y=\sqrt{\log_2 (\sin x)}.$

### `math-214` (math)

- gold: process_correct=False first_error=8 A_correct=False
- pred: process_correct=False first_error=9 type=THEOREM_MISUSE parse=SUCCESS
- reason: Step 9 misapplies Heron's formula to triangle ABC using sides 11,7,6 and conflates semiperimeter with leg length s; ABC's sides are s,s,s√2.
- problem: Isosceles $\triangle{ABC}$ has a right angle at $C$.  Point $P$ is inside $\triangle{ABC}$, such that $PA=11$, $PB=7$, and $PC=6$. Legs $\overline{AC}$ and $\overline{BC}$ have length $s=\sqrt{a+b\sqrt{2}}$, where $a$ and $b$ are positive integers. What is $a+b$?  [asy] pair A,B…

### `math-273` (math)

- gold: process_correct=False first_error=2 A_correct=False
- pred: process_correct=False first_error=1 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 1 incorrectly claims numbers in [30,50) round to 40; e.g., 45 does not. The valid rounding range is [35,44], so the stated condition is mathematically false.
- problem: Which of the following integers round to $40$ when rounded to the nearest ten? A. $43$ B. $23$ C. $38$ D. $51$ E. $45$ F. $35$ Express your answer as a block of letters corresponding to the answer choices that round to $40$, in alphabetic order with no punctuation. For example, …

### `math-546` (math)

- gold: process_correct=False first_error=4 A_correct=True
- pred: process_correct=False first_error=3 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 3 incorrectly asserts the leading digit is 1; the sum of the expansion terms is ~10^100 - 9^100, which has leading digit 9, not 1. The digit-count conclusion is right but justified wrongly.
- problem: How many digits are in the whole-number representation of $10^{100}-9^{100}$?

### `olympiadbench-67` (olympiadbench)

- gold: process_correct=False first_error=1 A_correct=False
- pred: process_correct=False first_error=3 type=ALGEBRA_ERROR parse=SUCCESS
- reason: Step 3 incorrectly writes AB/sin(∠ACB) = AB*(8/9); since sin(∠ACB)=8/9, division yields AB*(9/8), not AB*(8/9).
- problem: Let $T=3$. In $\triangle A B C, A C=T^{2}, \mathrm{~m} \angle A B C=45^{\circ}$, and $\sin \angle A C B=\frac{8}{9}$. Compute $A B$.

### `olympiadbench-658` (olympiadbench)

- gold: process_correct=False first_error=6 A_correct=True
- pred: process_correct=False first_error=3 type=ALGEBRA_ERROR parse=SUCCESS
- reason: Step 3 writes f(u)=(u^2-2u+1)+1-1, which simplifies to (u-1)^2, not the claimed (u-1)^2+1; the shown equality is false.
- problem: If $f(x)=\sin ^{2} x-2 \sin x+2$, what are the minimum and maximum values of $f(x)$ ?

### `olympiadbench-146` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=2 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 2 falsely claims y=⌈x⌉² is piecewise quadratic; it is piecewise constant (step function), so later trapezoid area model is invalid.
- problem: Let $T=20 \sqrt{7}$. Let $w>0$ be a real number such that $T$ is the area of the region above the $x$-axis, below the graph of $y=\lceil x\rceil^{2}$, and between the lines $x=0$ and $x=w$. Compute $\lceil 2 w\rceil$.

### `olympiadbench-551` (olympiadbench)

- gold: process_correct=False first_error=5 A_correct=True
- pred: process_correct=False first_error=2 type=THEOREM_MISUSE parse=SUCCESS
- reason: Step 2 misapplies the half-angle identity: stating 'letting θ=30°' yields cos(15°)=√((1+cos30°)/2) is invalid substitution (should be θ=15°), though the expression coincidentally matches.
- problem: If $0^{\circ}<x<90^{\circ}$ and $3 \sin (x)-\cos \left(15^{\circ}\right)=0$, what is the value of $x$ to the nearest tenth of a degree?

### `olympiadbench-438` (olympiadbench)

- gold: process_correct=False first_error=4 A_correct=False
- pred: process_correct=False first_error=2 type=ALGEBRA_ERROR parse=SUCCESS
- reason: Step 2 erroneously rewrites the RHS term 3^x as 3^x(3^2)=9*3^x, which is not equivalent to the original equation.
- problem: Determine all real values of $x$ for which  $$ 3^{x+2}+2^{x+2}+2^{x}=2^{x+5}+3^{x} $$

### `olympiadbench-141` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=2 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 2 wrongly concludes that setting y=f(f(x)) makes the original equation y=3; correctly, f(y)=3 must hold, not y=3.
- problem: Consider the function $f(x)=x^{2}-2 x$. Determine all real numbers $x$ that satisfy the equation $f(f(f(x)))=3$.

### `olympiadbench-48` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=2 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 2 claims 2908 is valid because its digit sum 19 exceeds 17, but the problem requires the sum to be exactly 17.
- problem: Compute the least integer greater than 2023 , the sum of whose digits is 17 .

### `olympiadbench-811` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=True
- pred: process_correct=False first_error=2 type=PROBLEM_MISREAD parse=SUCCESS
- reason: For n=3, the Shiny condition requires y1y2+y2y3 >= -1 for every permutation, not the sum of all three pairwise products x1x2+x2x3+x3x1 >= -1; step misreads the adjacent sum definition.
- problem: An integer $n \geqslant 3$ is given. We call an $n$-tuple of real numbers $\left(x_{1}, x_{2}, \ldots, x_{n}\right)$ Shiny if for each permutation $y_{1}, y_{2}, \ldots, y_{n}$ of these numbers we have  $$ \sum_{i=1}^{n-1} y_{i} y_{i+1}=y_{1} y_{2}+y_{2} y_{3}+y_{3} y_{4}+\cdots…

### `olympiadbench-479` (olympiadbench)

- gold: process_correct=False first_error=4 A_correct=False
- pred: process_correct=False first_error=5 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 5 omits the prime factor 17, which is itself a two-digit factor, and implies only three such factors exist.
- problem: Compute the sum of all positive two-digit factors of $2^{32}-1$.

### `olympiadbench-11` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=1 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 1 ignores the condition that six extra digits were inserted into the repetend and misreads $.0\overline{0231846597}$ as $0.\overline{0231846597}$, treating the corrupted decimal as the true expansion of 1/N.
- problem: A student computed the repeating decimal expansion of $\frac{1}{N}$ for some integer $N$, but inserted six extra digits into the repetend to get $.0 \overline{0231846597}$. Compute the value of $N$.

### `olympiadbench-117` (olympiadbench)

- gold: process_correct=False first_error=8 A_correct=False
- pred: process_correct=False first_error=10 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 10 chooses k=1 to maximize a+b but ignores the condition floor(ab)=k; with k=1, a>18 and b>17 so ab>300, making floor(ab)≠1. Also miscomputes 38-2(1)-2 as 36.
- problem: Given that $a$ and $b$ are positive and  $$ \lfloor 20-a\rfloor=\lfloor 19-b\rfloor=\lfloor a b\rfloor, $$  compute the least upper bound of the set of possible values of $a+b$.

### `olympiadbench-348` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=2 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 2 falsely asserts HA is an edge or face diagonal of one of the tetrahedra; H and A are in different tetrahedra, and the subsequent assumption that H,A,E form an equilateral triangle is unsupported.
- problem: Regular tetrahedra $J A N E, J O H N$, and $J O A N$ have non-overlapping interiors. Compute $\tan \angle H A E$.

### `olympiadbench-114` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=1 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 1 incorrectly asserts only 2-step paths are allowed; non-shortest self-avoiding paths (e.g., (0,0)->(0,1)->(0,2)->(1,2)->(1,1)) exist under the rules.
- problem: Derek starts at the point $(0,0)$, facing the point $(0,1)$, and he wants to get to the point $(1,1)$. He takes unit steps parallel to the coordinate axes. A move consists of either a step forward, or a $90^{\circ}$ right (clockwise) turn followed by a step forward, so that his …

### `olympiadbench-780` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=True
- pred: process_correct=False first_error=9 type=HALLUCINATION parse=SUCCESS
- reason: Step 9 falsely asserts sin12° sin24° sin42° = (√5-1)/16, which is incorrect (actual product ≈0.0566).
- problem: Compute the value of  $$ \sin \left(6^{\circ}\right) \cdot \sin \left(12^{\circ}\right) \cdot \sin \left(24^{\circ}\right) \cdot \sin \left(42^{\circ}\right)+\sin \left(12^{\circ}\right) \cdot \sin \left(24^{\circ}\right) \cdot \sin \left(42^{\circ}\right) \text {. } $$

### `olympiadbench-182` (olympiadbench)

- gold: process_correct=False first_error=5 A_correct=False
- pred: process_correct=False first_error=4 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 4 falsely claims a positive integer cannot end in 0 and misstates the carry condition (d>=1 for unit carry, not 0<d<1), invalidating the case analysis.
- problem: Compute the least positive integer $n$ such that the sum of the digits of $n$ is five times the sum of the digits of $(n+2019)$.

### `omnimath-305` (omnimath)

- gold: process_correct=False first_error=16 A_correct=False
- pred: process_correct=False first_error=13 type=ARITHMETIC_ERROR parse=SUCCESS
- reason: Step 13 falsely asserts 60 = 5^2 + 6^2 = 61, which is incorrect arithmetic.
- problem: We consider positive integers $n$ having at least six positive divisors. Let the positive divisors of $n$ be arranged in a sequence $(d_i)_{1\le i\le k}$ with $$1=d_1<d_2<\dots <d_k=n\quad (k\ge 6).$$ Find all positive integers $n$ such that $$n=d_5^2+d_6^2.$$

### `omnimath-861` (omnimath)

- gold: process_correct=False first_error=1 A_correct=True
- pred: process_correct=False first_error=2 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 2 erroneously states n!+1 divides (n+1)!+1 iff it divides (n+1)!+1-(n+1)n!, but (n+1)n! is not a multiple of n!+1, breaking divisibility rules; later algebra is also nonsensical.
- problem: Is the set of positive integers $n$ such that $n!+1$ divides (2012n)! finite or infinite?

### `omnimath-203` (omnimath)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=2 type=ALGEBRA_ERROR parse=SUCCESS
- reason: Step 2 sets c=f(0) but incorrectly replaces f(f(0)) with c; f(f(0))=f(c), not necessarily c.
- problem: Find all functions $f:\mathbb{R}\to \mathbb{R}$ such that  $$f(x)+f(yf(x)+f(y))=f(x+2f(y))+xy$$for all $x,y\in \mathbb{R}$.

### `omnimath-165` (omnimath)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=2 type=ARITHMETIC_ERROR parse=SUCCESS
- reason: Step 2 falsely claims 1547 = 23 × 67; actually 23×67 = 1541.
- problem: How many positive integers less than 1998 are relatively prime to 1547 ? (Two integers are relatively prime if they have no common factors besides 1.)

### `omnimath-314` (omnimath)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=4 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 4 falsely claims the 10th student is among the 7 solvers of each problem, but the problem only states each problem was solved by exactly 7 of the 10 students, not necessarily the 10th.
- problem: A class of 10 students took a math test. Each problem was solved by exactly 7 of the students. If the first nine students each solved 4 problems, how many problems did the tenth student solve?

### `omnimath-245` (omnimath)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=False first_error=8 type=LOGIC_GAP parse=SUCCESS
- reason: Step 8 claims without justification that the triangle must be isosceles and then concludes BC=√164, which neither follows from prior steps nor satisfies the given condition (e.g., a right triangle with legs 8,10 fails the bisecting condition).
- problem: In triangle $A B C$ with $A B=8$ and $A C=10$, the incenter $I$ is reflected across side $A B$ to point $X$ and across side $A C$ to point $Y$. Given that segment $X Y$ bisects $A I$, compute $B C^{2}$.

### `omnimath-80` (omnimath)

- gold: process_correct=False first_error=5 A_correct=False
- pred: process_correct=False first_error=3 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 3 incorrectly states v_p(x+a_i) increases by exactly 1 each time x hits -a_i mod p, ignoring that valuations can jump by more than 1 at higher powers of p.
- problem: For a given positive integer $n$ and prime number $p$, find the minimum value of positive integer $m$ that satisfies the following property: for any polynomial $$f(x)=(x+a_1)(x+a_2)\ldots(x+a_n)$$ ($a_1,a_2,\ldots,a_n$ are positive integers), and for any non-negative integer $k$…

### `omnimath-87` (omnimath)

- gold: process_correct=False first_error=4 A_correct=False
- pred: process_correct=False first_error=2 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 2 computes the full container volume using given height 10 cm as water height, misreading that water height is unknown and equal, not the container height.
- problem: Mike has two containers. One container is a rectangular prism with width 2 cm, length 4 cm, and height 10 cm. The other is a right cylinder with radius 1 cm and height 10 cm. Both containers sit on a flat surface. Water has been poured into the two containers so that the height …

### `omnimath-433` (omnimath)

- gold: process_correct=False first_error=4 A_correct=False
- pred: process_correct=False first_error=2 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 2 incorrectly asserts triangles BCD and CDE are right-angled; the given right angles are ∠ACD and ∠ADE, not ∠BCD or ∠CDE.
- problem: Let $A B C D E$ be a convex pentagon such that $\angle A B C=\angle A C D=\angle A D E=90^{\circ}$ and $A B=B C=C D=D E=1$. Compute $A E$.

### `omnimath-408` (omnimath)

- gold: process_correct=False first_error=2 A_correct=False
- pred: process_correct=False first_error=1 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 1 mismodels the scale: a balance reading reliably indicates equal weights, while left/right readings can be deceptive; treating the third outcome as 'no information' is conceptually wrong and invalidates the subsequent 3^k >= 2n bound.
- problem: We have $n{}$ coins, one of which is fake, which differs in weight from the real ones and a two-pan scale which works correctly if the weights on the pans are different, but can show any outcome if the weights on the pans are equal. For what $n{}$ can we determine which coin is …

### `omnimath-665` (omnimath)

- gold: process_correct=False first_error=3 A_correct=True
- pred: process_correct=False first_error=2 type=CONDITION_OMISSION parse=SUCCESS
- reason: Step 2 substitutes a=1 and asserts 1+f(b) | 1+bf(1) for (implicitly) all b, ignoring the problem's requirement a+b>2019 (so b>=2019).
- problem: Find all functions $f:\mathbb Z_{>0}\to \mathbb Z_{>0}$ such that $a+f(b)$ divides $a^2+bf(a)$ for all positive integers $a$ and $b$ with $a+b>2019$.

### `omnimath-253` (omnimath)

- gold: process_correct=False first_error=7 A_correct=False
- pred: process_correct=False first_error=3 type=PROBLEM_MISREAD parse=SUCCESS
- reason: Step 3 incorrectly models the system as P(t)=w+xt+yt^2+zt^3 at t=1,2,3,4; actually the 2nd eq is 2w+4x+8y+16z = 2*P(2) ≠ P(2), so the values assigned to P(2),P(3),P(4) are wrong.
- problem: Let $w, x, y, z$ be real numbers such that $w+x+y+z =5$, $2 w+4 x+8 y+16 z =7$, $3 w+9 x+27 y+81 z =11$, $4 w+16 x+64 y+256 z =1$. What is the value of $5 w+25 x+125 y+625 z ?$

### `omnimath-346` (omnimath)

- gold: process_correct=False first_error=7 A_correct=False
- pred: process_correct=False first_error=9 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 9 falsely claims bc=1 implies b=1 or c=1 and assumes b,c must be integers, both invalid for positive reals.
- problem: Find all ordered triples $(a, b, c)$ of positive reals that satisfy: $\lfloor a\rfloor b c=3, a\lfloor b\rfloor c=4$, and $a b\lfloor c\rfloor=5$, where $\lfloor x\rfloor$ denotes the greatest integer less than or equal to $x$.

### `omnimath-72` (omnimath)

- gold: process_correct=False first_error=5 A_correct=False
- pred: process_correct=False first_error=4 type=CONCEPT_ERROR parse=SUCCESS
- reason: Step 4 falsely claims the parity constraint can be ignored because (8,14) has even sum; paths to it can still pass through both-odd points, so the constraint cannot be dropped.
- problem: A frog is at the point $(0,0)$. Every second, he can jump one unit either up or right. He can only move to points $(x, y)$ where $x$ and $y$ are not both odd. How many ways can he get to the point $(8,14)$?

## PARSE_FAIL — prediction unusable (8)

### `olympiadbench-25` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=None first_error=None type=None parse=FAILURE
- problem: In the coordinate plane consider the set $S$ of all points with integer coordinates. For a positive integer $k$, two distinct points $A, B \in S$ will be called $k$-friends if there is a point $C \in S$ such that the area of the triangle $A B C$ is equal to $k$. A set $T \subset…

### `olympiadbench-665` (olympiadbench)

- gold: process_correct=False first_error=4 A_correct=True
- pred: process_correct=None first_error=None type=None parse=FAILURE
- problem: Compute the number of five-digit integers $\underline{M} \underline{A} \underline{R} \underline{T} \underline{Y}$, with all digits distinct, such that $M>A>R$ and $R<T<Y$.

### `olympiadbench-216` (olympiadbench)

- gold: process_correct=False first_error=2 A_correct=False
- pred: process_correct=None first_error=None type=None parse=FAILURE
- problem: For real numbers $\alpha, B$, and $C$, the zeros of $T(x)=x^{3}+x^{2}+B x+C \operatorname{are~}^{2} \alpha$, $\cos ^{2} \alpha$, and $-\csc ^{2} \alpha$. Compute $T(5)$.

### `olympiadbench-469` (olympiadbench)

- gold: process_correct=False first_error=5 A_correct=False
- pred: process_correct=None first_error=None type=None parse=FAILURE
- problem: Consider the system of equations:  $$ \begin{aligned} c+d & =2000 \\ \frac{c}{d} & =k \end{aligned} $$  Determine the number of integers $k$ with $k \geq 0$ for which there is at least one pair of integers $(c, d)$ that is a solution to the system.

### `olympiadbench-142` (olympiadbench)

- gold: process_correct=False first_error=3 A_correct=False
- pred: process_correct=None first_error=None type=None parse=FAILURE
- problem: Find all positive integers $n$ for which all positive divisors of $n$ can be put into the cells of a rectangular table under the following constraints:  - each cell contains a distinct divisor; - the sums of all rows are equal; and - the sums of all columns are equal.

### `olympiadbench-642` (olympiadbench)

- gold: process_correct=False first_error=1 A_correct=True
- pred: process_correct=None first_error=None type=None parse=FAILURE
- problem: Compute the smallest possible value of $n$ such that two diagonals of a regular $n$-gon intersect at an angle of 159 degrees.

### `omnimath-519` (omnimath)

- gold: process_correct=False first_error=4 A_correct=True
- pred: process_correct=None first_error=None type=None parse=FAILURE
- problem: Stan has a stack of 100 blocks and starts with a score of 0, and plays a game in which he iterates the following two-step procedure: (a) Stan picks a stack of blocks and splits it into 2 smaller stacks each with a positive number of blocks, say $a$ and $b$. (The order in which t…

### `omnimath-462` (omnimath)

- gold: process_correct=False first_error=5 A_correct=False
- pred: process_correct=None first_error=None type=None parse=FAILURE
- problem: You start with a single piece of chalk of length 1. Every second, you choose a piece of chalk that you have uniformly at random and break it in half. You continue this until you have 8 pieces of chalk. What is the probability that they all have length $\frac{1}{8}$ ?

## API_FAIL — provider/transport error (0)

_none_
