-- =============================================
-- 1. 创建用户状态枚举类型（必须前置）
-- =============================================
CREATE TYPE user_status AS ENUM ('enabled', 'disabled');

-- =============================================
-- 2. 创建用户表（移除所有行内COMMENT，仅保留核心结构）
-- =============================================
CREATE TABLE t_user (
    -- 主键：用户ID，自增
    user_id SERIAL PRIMARY KEY,
    user_code VARCHAR(64) NOT NULL UNIQUE,
    -- 核心字段：用户名/账号/密码
    user_name VARCHAR(64) NOT NULL,
    user_account VARCHAR(64) NOT NULL UNIQUE,
    user_password BYTEA NOT NULL,
    -- 预留扩展字段（按需启用，默认允许为空）
    user_phone VARCHAR(20),
    user_email VARCHAR(128),
    user_role VARCHAR(32) DEFAULT 'normal',
    user_dept VARCHAR(64),
    -- 用户状态：枚举类型，默认启用
    status user_status NOT NULL DEFAULT 'enabled',
    -- 审计字段：创建/更新时间
    create_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 预留扩展字段（JSON格式存储非结构化信息）
    ext_info JSONB
);

-- =============================================
-- 3. 添加表/字段注释（PostgreSQL标准写法）
-- =============================================
-- 表注释
COMMENT ON TABLE t_user IS '用户信息表（含核心字段+预留扩展字段）';

-- 字段注释
COMMENT ON COLUMN t_user.user_id IS '用户ID（主键）';
COMMENT ON COLUMN t_user.user_code IS '用户编号（唯一）';
COMMENT ON COLUMN t_user.user_name IS '用户姓名';
COMMENT ON COLUMN t_user.user_account IS '用户登录账号（唯一）';
COMMENT ON COLUMN t_user.user_password IS '用户密码（加密存储，禁止明文）';
COMMENT ON COLUMN t_user.user_phone IS '预留：用户手机号（唯一）';
COMMENT ON COLUMN t_user.user_email IS '预留：用户邮箱（唯一）';
COMMENT ON COLUMN t_user.user_role IS '预留：用户角色（admin/normal/operator）';
COMMENT ON COLUMN t_user.user_dept IS '预留：用户所属部门';
COMMENT ON COLUMN t_user.status IS '用户状态（enabled=启用，disabled=禁用）';
COMMENT ON COLUMN t_user.create_time IS '用户记录创建时间';
COMMENT ON COLUMN t_user.update_time IS '用户记录更新时间';
COMMENT ON COLUMN t_user.ext_info IS '预留：用户扩展信息（JSON格式，如头像、备注等）';

-- 手机号/邮箱：非空时唯一索引
CREATE UNIQUE INDEX idx_user_phone ON t_user (user_phone) WHERE user_phone IS NOT NULL;
CREATE UNIQUE INDEX idx_user_email ON t_user (user_email) WHERE user_email IS NOT NULL;

-- 常用查询字段：普通索引
CREATE INDEX idx_user_code ON t_user (user_code);
CREATE INDEX idx_user_account ON t_user (user_account);
CREATE INDEX idx_user_status ON t_user (status);
CREATE INDEX idx_user_role ON t_user (user_role);