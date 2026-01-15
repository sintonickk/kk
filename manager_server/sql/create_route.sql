
CREATE TYPE file_format AS ENUM ('gps', 'txt', 'json');

-- 创建路线表（存储路线基础信息，具体点位在外部文件中）
CREATE TABLE t_route (
    -- 自增主键ID
    route_id SERIAL PRIMARY KEY,
    -- 路线名称（非空，如"XX厂区巡检路线01"）
    route_name VARCHAR(128) NOT NULL,
    -- 路线文件路径（非空，存储文件的绝对路径/相对路径，如"/data/route/route_001.gps"）
    route_file_path VARCHAR(1024) NOT NULL UNIQUE,
    -- 上传人CODE（关联用户表t_user的user_code）
    upload_user_code VARCHAR(64),
    -- 路线描述（可选，备注路线用途、范围等）
    route_desc TEXT,
    -- 路线文件格式（可选，如gps、txt、json等）
    route_format file_format NOT NULL DEFAULT 'gps',
    -- 创建时间（默认当前时间，不可修改）
    create_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 修改时间（默认当前时间，更新时自动刷新）
    update_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 外键约束：关联用户表（确保上传人ID存在）
    CONSTRAINT fk_route_upload_user FOREIGN KEY (upload_user_code) REFERENCES t_user (user_code)
        ON DELETE SET NULL  -- 用户删除时，上传人ID置空，保留路线记录
        ON UPDATE CASCADE   -- 用户ID更新时，同步更新
);

-- 添加表/字段注释（PostgreSQL标准写法）
COMMENT ON TABLE t_route IS '路线基础信息表（具体点位存储在外部文件中）';
COMMENT ON COLUMN t_route.route_id IS '路线ID（自增主键）';
COMMENT ON COLUMN t_route.route_name IS '路线名称';
COMMENT ON COLUMN t_route.route_file_path IS '路线文件存储路径（绝对/相对路径）';
COMMENT ON COLUMN t_route.upload_user_code IS '路线上传人CODE（关联t_user表）';
COMMENT ON COLUMN t_route.route_desc IS '路线描述（备注路线用途、覆盖范围等）';
COMMENT ON COLUMN t_route.route_format IS '路线文件格式（如gps/txt/json）';
COMMENT ON COLUMN t_route.create_time IS '路线记录创建时间';
COMMENT ON COLUMN t_route.update_time IS '路线记录最后修改时间';

-- 创建索引（提升查询效率）
CREATE INDEX idx_route_upload_user ON t_route (upload_user_code);  -- 按上传人查询路线
CREATE INDEX idx_route_create_time ON t_route (create_time);    -- 按创建时间筛选
CREATE INDEX idx_route_name ON t_route (route_name);            -- 按路线名模糊查询
CREATE UNIQUE INDEX idx_route_file_path ON t_route (route_file_path);  -- 确保文件路径唯一