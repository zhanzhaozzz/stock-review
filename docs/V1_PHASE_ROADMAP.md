# Stock Review V1 阶段路线图

## 文档目的

本文件用于把 V1 的所有实施阶段串成一条完整路线，方便按文档逐步开发。

## 阶段总览

### Phase 0

[PHASE_0_ENUM_TERM_CLEANUP.md](/Users/zhanzhao/项目/stock-review/docs/PHASE_0_ENUM_TERM_CLEANUP.md)

目标：

- 统一词汇
- 清理旧词
- 消除语义漂移

### Phase 1

[PHASE_1_V1_CORE_OBJECT_MODELING.md](/Users/zhanzhao/项目/stock-review/docs/PHASE_1_V1_CORE_OBJECT_MODELING.md)

目标：

- 新建四个核心对象
- 完成 model/schema/service/API 骨架

### Phase 2

[PHASE_2_GENERATION_PIPELINE_AND_SCHEDULER.md](/Users/zhanzhao/项目/stock-review/docs/PHASE_2_GENERATION_PIPELINE_AND_SCHEDULER.md)

目标：

- 打通对象生成链
- 重排 Scheduler
- 提供手动兜底入口

### Phase 3

[PHASE_3_FRONTEND_PAGE_MIGRATION.md](/Users/zhanzhao/项目/stock-review/docs/PHASE_3_FRONTEND_PAGE_MIGRATION.md)

目标：

- 前端切换到三大主页面
- 页面职责归位

### Phase 4

[PHASE_4_VALIDATION_AND_CUTOVER.md](/Users/zhanzhao/项目/stock-review/docs/PHASE_4_VALIDATION_AND_CUTOVER.md)

目标：

- 并行验证
- 切换收口
- 确认 V1 可作为主系统

## 推荐施工顺序

严格按阶段推进：

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4

不建议跳阶段并行大规模施工。

## 每阶段完成判断

### Phase 0 完成标志

- 项目只剩一套规范词

### Phase 1 完成标志

- 四个核心对象在数据库和后端有正式落点

### Phase 2 完成标志

- 四对象能按交易日时间轴自动或手动生成

### Phase 3 完成标志

- 前端三大主页面改造完成

### Phase 4 完成标志

- 新 V1 作战流能替代旧主流程，成为日常主系统

## 最终一句话

`stock-review V1` 的实施路径是：

`统一语言 -> 落地对象 -> 打通生成链 -> 切换页面 -> 验证收口`
