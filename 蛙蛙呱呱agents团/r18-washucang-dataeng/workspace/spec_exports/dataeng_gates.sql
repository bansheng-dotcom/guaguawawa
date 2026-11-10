-- R18 DATAENG_SPEC v1.0 自动编译；禁止手改，改账本后重导
CREATE TABLE IF NOT EXISTS dq_gate_rules (
  table_name      VARCHAR(128) NOT NULL,
  max_null_ratio  DOUBLE NOT NULL DEFAULT 0.1 CHECK (max_null_ratio = 0.1),
  max_dup_ratio   DOUBLE NOT NULL DEFAULT 0.05 CHECK (max_dup_ratio = 0.05),
  max_age_hours   INT    NOT NULL DEFAULT 24 CHECK (max_age_hours = 24),
  min_row_count   INT    NOT NULL DEFAULT 1 CHECK (min_row_count >= 1),
  conservation_tolerance DOUBLE NOT NULL DEFAULT 0.0 CHECK (conservation_tolerance = 0.0)
);

-- 北极星指标：作为下游 BI 的指标字典（口径唯一）
-- PSR 管道成功率: 成功批次 / 总批次（按调度批次计） → ≥ 99.5%
-- FSR 新鲜度达标率: age_hours ≤ SLA 的批次 / 总批次 → ≥ 99.0%
-- DQR 质量合格率: 通过质量门禁的表数 / 纳管表数 → ≥ 98.0%
-- LCR 血缘覆盖率: 上下游完整登记的表 / 纳管表数 → = 100%
-- BCR 回填合规率: 带审批凭据的回填 / 总回填 → = 100%
-- MTTD 故障发现时延: 从异常发生到告警触发的分钟数 → ≤ 15 min
-- DMR 重复率上限: 去重后行数 / 总行数的补数 → ≤ 5.0%
-- ORT 越界行数: 数值列超出声明区间的行数 → = 0
