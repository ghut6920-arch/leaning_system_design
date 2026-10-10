你写的 `u=x、dv=e^x dx、du=dx、v=e^x` 都正确。现在只需把它们接到分部积分公式：

\[
\int u\,dv=uv-\int v\,du.
\]

这是本题允许查阅的输入，不需要先背下来。[公式来源：OpenStax](https://openstax.org/books/calculus-volume-2/pages/3-1-integration-by-parts)

原积分正是 `∫u dv`，因此在你现有四项下面续写：

\[
\int xe^x\,dx
=x e^x-\int e^x\,dx.
\]

第一项来自 `u·v`，后面的积分来自 `v·du=e^x dx`，前面保留公式中的减号。你接下来只需算这个剩下的 `∫e^x dx`，并在最终原函数写上积分常数 `C`；继续写在同一份解答里即可。
