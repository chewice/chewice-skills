# STARsolo read geometry 判定

仅用于有 10x/droplet scRNA 证据的 `workflow=sra` 样本。ATAC-seq、ChIP-seq、miRNA-seq、bulk RNA-seq 不要套用本节。

## 必须判定角色，不得假设

对于标准 10x 3' 文库，STARsolo 通常先接收 cDNA reads，再接收 barcode/UMI reads，尽管对应文件通常命名为 R2 和 R1。必须根据实验确认，不能将此规则全局套用。

检查：

- kit/chemistry 版本；
- R1/R2/I1/I2 长度；
- 提交文件名和 run aliases；
- barcode 与 UMI 位置；
- 原始 kit 使用的 whitelist；
- SRA 转换是否暴露 technical reads。

由 `fasterq-dump --include-technical` 生成的 technical reads 不得自动输入 STARsolo。部分归档可暴露两个以上的 reads，必须明确映射其角色。

## 常见 10x 默认值

以下仅用于提示，不能代替数据集证据：

| Chemistry | CB | UMI | 常见 whitelist |
|---|---:|---:|---|
| 10x 3' v2 | 16 | 10 | `737K-august-2016.txt` |
| 10x 3' v3 | 16 | 12 | `3M-february-2018.txt` |

部分 v3 数据集会暴露 10-base UMI 或经过 trimming 的 barcode read。必须遵循实际实验设置与 read 长度。

## 可复现性

- 锁定一个 STAR 版本。
- 使用完全相同的版本建立并运行 genome index。
- 记录参考名称、FASTA/GTF release、`sjdbOverhang`、whitelist、geometry、STAR 命令和工具版本。
- 不得复用由未知或不兼容 STAR 版本建立的 index。

## Velocity 交付物

用户要求 velocity 时校验：

- raw 和 filtered 10x `matrix.mtx.gz`、`features.tsv.gz`、`barcodes.tsv.gz`；
- spliced、unspliced 和 ambiguous 矩阵；
- velocity features 和 barcodes；
- loom layer 名称与 shape；
- raw/filtered/velocity feature 维度和 filtered loom cell 维度。
