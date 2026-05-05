\# Finding 记录：TikTok LIVE 政策页面的 CSR 架构 vs 主站 SSR 架构



日期：\[今天]



\## 现象

在第二步数据采集中，6 个 LIVE 类政策文件下载下来只有 \~3 KB，且内容只是一个空 HTML 框架加上一个 JS 加载器（`tiktok\_privacy\_protection\_framework`），没有任何政策正文。这些文件覆盖 2024-09 到 2025-08 期间的 LIVE Monetization Guidelines。



\## 技术解释

TikTok LIVE 政策页面采用客户端动态渲染（CSR）架构——服务器返回的是 HTML 壳子，真实内容由 JavaScript 在浏览器端调用 API 渲染。Wayback Machine 在归档静态资源时无法触发 JS 执行，只能拿到壳子。



\## 与主站 CG 的对比

TikTok 主站 Community Guidelines (`tiktok.com/community-guidelines/en`) 采用服务端渲染（SSR），HTML 直接包含完整政策正文，所以同一时期 Wayback 上有 173 个有效快照。同样是 TikTok 的政策文档，主站可被研究者完整追溯，LIVE 政策却几乎不可被归档。



\## 研究意义

这不只是一个数据缺陷，它是治理透明度差异的证据。SSR 主站政策天然便于第三方（研究者、记者、监管者）历史归档审计；CSR 直播政策则因架构选择丧失了被独立监督的可能。无论 TikTok 是否有意为之，这种架构选择构成了"直播治理黑箱化"的技术基础设施。



\## 如何在论文中使用

\- \*\*Limitations 章节\*\*：诚实交代 LIVE 类样本量受限于 CSR 架构。

\- \*\*Discussion 章节\*\*：把这个观察延伸为一个理论论点——"治理透明度的不平等不仅来自政策文本本身的开放程度，也来自承载政策文本的技术架构"。

\- \*\*可挂的文献\*\*：Bucher (2018) \*If...Then: Algorithmic Power and Politics\*；Plantin et al. (2018) on infrastructure studies；Gillespie (2018) on platform opacity。

