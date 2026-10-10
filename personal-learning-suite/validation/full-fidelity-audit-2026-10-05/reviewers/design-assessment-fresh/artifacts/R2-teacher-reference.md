# R2 教师完整参考（备课，不自动作为当前可见输入）

```python
def lower_bound(a, target):
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo
```

不变量：0≤lo≤hi≤n；所有i<lo有a[i]<target；所有hi≤i<n有a[i]≥target。初始化lo=0,hi=n，两边范围均空，成立。若a[mid]<target，则非降序保证i≤mid全部不合格，更新lo=mid+1保留不变量。若a[mid]≥target，则i≥mid全部合格，更新hi=mid保留不变量。循环内mid<n，访问合法。自然数hi-lo在每轮严格缩短，因此终止。终止lo=hi，左侧都不合格；若lo<n，该位置合格，故最小；若lo=n，所有元素不合格，符合不存在分支。代码不写列表。复杂度可由区间至多约减半得O(log(n+1))时间、O(1)额外空间。

这份整体证明与280个有限运行是不同依据。教师参考已核，不是学习者提交或修订；展示给学习者时改变相应帮助条件，不生成自主实现／自主证明支持。
