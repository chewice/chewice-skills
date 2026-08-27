# Provenance 与来源路由（兼容入口）

新合同见 `sources/` 下与实际来源匹配的 reference，以及顶层 `source_capability.yaml`。

核心规则：先按对象保真度与下游需求选择 object class，再选择 transport endpoint；用户明确来源优先。provenance 来自官方对象分类，不由镜像位置、文件名或 Phred 分布推断。`fallback_reason` 仅为旧 manifest 兼容字段；新记录使用 `selection_evidence` 与 `selection_reason`。
