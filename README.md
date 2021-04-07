<p align="center">
  <a href="https://github.com/montali/lp-money-machine">
    <img src="https://user-images.githubusercontent.com/3484085/113842129-ab4e8000-9792-11eb-8555-471d6cbc3f69.png" alt="Logo" width="130" height="130">
  </a>
  <h1 align="center">LP Money Machine</h1>

  <p align="center">
    Stock optimizer.
  </p>
</p>

## Decision variables

First of all, we'll have to state the decision variables: a good choice would probably be considering a stock symbol as a decision variable, e.g. AAPL=1 meaning buying 1$ worth of Apple stocks. We wouldn't though be considering an important aspect: the **time dimension**. We all know that stocks are strictly time-related. A baseline approach to this is obviously considering our portfolio to be static, i.e. that we can't sell/buy except from day 0 and day -1 (i.e. the last day in *pythonic jargon*).

A further improvement in this approach would be considering as decision variables something like *Stock in my portfolio at day X*, like AAPL5=1 would state that we have 1$ worth of Apple stocks, in day 5. This would obviously scale our problem's size to a much, much more complex one. 

## Data

We'll initially want to consider a daily average of stocks, to avoid getting lots of similar/useless data. Another smart idea would probably be only keeping track of the most interesting stocks, and avoiding downloading data for stocks we're not interested in. The [S&P 500](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies) is probably a good choice.

Choosing a kinda known index is a good choice for lots of reasons, the first being that we can find [ready-to-use datasets](https://www.kaggle.com/camnugent/sandp500) of the history of prices. This makes the data retrieval part of the job painless. In the future, I'd like to implement something that automatically gathers data for a given company, maybe using [iex cloud](https://iexcloud.io/core-data/) or a Python scraper.

## Constraints

Every problem comes with some constraints. The first, obvious constraint is that we want to **respect our budget**, let's say 1000\$. Someone may that our variables should always be positive (*you can't sell something that you haven't bought*), but fortunately we live in an era in which [options](https://www.nerdwallet.com/article/investing/options-vs-stocks) are available. The difference in stocks vs. options is that, in the latter, we are not effectively buying a stock, we're just *betting on the stock's direction*. Nowadays, most of the beginner investors start with CFDs, i.e. *Contracts for Difference*, which are somewhat similar to options. The crucial point of this differentiation with stocks is one: **we're now able to place puts and calls**, similar to **sell** and **buy** positions, although **we can bet on the price drop**, i.e. we can sell without buying. This eliminates the $\ge0$ constraint for our variables.

