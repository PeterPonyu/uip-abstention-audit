# AGENTS.md — materials-mlip-research (isolated workspace)

新研究工作区，与既有 sibling 工作区（含 `dl-research`）**隔离**。
主题：**材料 / 催化机器学习势 (MLIP) 与晶体性质预测的可靠性、校准、外推与数据泄漏审计**。

既有可靠性方法论向材料信息学的迁移。核心母题不变：*低回归误差 (MAE/RMSE) ≠ 可靠的决策*。
材料版本：*能量/力的回归精度高，不代表稳定性分类可靠，也不代表 MD 物理自洽。*

## 隔离规则
- 不读取/修改既有 sibling 工作区（含 `dl-research`）的 artifacts；旧结论只当口头背景。
- 研究记录只写本目录 `research/`、`notes/`、`plans/`；编号用 `MT1…`。

## 研究边界
允许：
- MLIP / 晶体能量模型（CGCNN、M3GNet、CHGNet、MACE、ORB、Equiformer、SevenNet 等 UIP）在公开基准上的
  **可靠性/校准/外推/泄漏**评测（推理 + 经典 ML 基线，不从头训练大模型）；
- 稳定性分类 vs 回归错配审计（convex-hull 0 eV/atom 决策边界附近的假阳性）；
- 选择性弃答层（在决策边界附近 abstain）；
- MD 能量守恒 OOD 审计（non-conservative direct-force vs gradient-based 负对照）；
- 排行榜泄漏/test-set 污染审计（prototype-match 去重、记忆诊断）。

默认排除：
- 从头训练通用势 / GNN 大模型（12GB 不现实，非贡献点）；
- 真实新材料发现 / 合成可行性断言（结论是基准可靠性，**非发现声明**）；
- 需大规模 DFT 自算的实验（无本地 DFT 预算）。

## 本地资源快照
- 计算：远程 `dl4080`（RTX 4080 Laptop **12GB**, torch 2.4.1+cu121, ~38GB 可用磁盘——子集优先）。
- 工具：RDKit / sklearn / torch 在册；MLIP 推理需装 `mace-torch` / `chgnet` / `matbench-discovery`（PyPI，pip 轻量）。
- **免注册公开基准/数据**：
  - **Matbench Discovery**（Nature MI 2025, Apache/MIT）— Figshare 自动缓存（默认 `~/.cache/matbench-discovery`），
    MP 训练集 154,719 + WBM 测试集 256,963 ComputedStructureEntries；在线 leaderboard + PyPI 包；
  - **MLIP Arena**（arXiv 2509.20630, 2025）— MD/能量守恒/物理一致性测评协议；
  - Materials Project（API key 免费）、OQMD、Open Catalyst OC20/**OC22**（62,331 relaxations，已核验）。

## Preferred research style（每候选必给）
1. 机制问题（可证伪）；2. 计算实验形态；3. 工业价值；4. 12GB/~38GB 可行性（**推理 + 经典 ML 基线**）；
5. Stage-0 最小可证伪 + kill 阈值；6. 风险/kill；7. 最近来源（DOI/repo）。

## 证据标准（沿用既有证据标准）
leakage-controlled split（**Matbench Discovery 自带** prototype-match 去重 + 5 步 OOD 替换梯度）·
预注册 metric + kill 阈值 · 判别/分类门 + bootstrap/Wald CI · 负对照（gradient-based force model；shuffle）·
校准（temperature/conformal）· 去循环（污染/记忆诊断）。
**关键纪律——不引用被否决断言：** OC20→OC22 "微调后能量预测改善 ~36% 体现 OOD 迁移失败"（本轮 0-3 否决）；
OC22 数据集本身的事实（62,331 relaxations）仍成立，只是该迁移叙事被否。
