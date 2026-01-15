-- 第一步：先创建报警处理状态枚举类型（必须前置）
CREATE TYPE alarm_process_status AS ENUM ('unprocessed', 'processing', 'closed', 'ignore');

-- 第二步：创建报警信息表（移除行内COMMENT，保留核心结构）
CREATE TABLE t_alarm_info (
    alarm_id SERIAL PRIMARY KEY,
    alarm_time TIMESTAMP WITH TIME ZONE NOT NULL,
    longitude NUMERIC(10, 7) NOT NULL,
    latitude NUMERIC(10, 7) NOT NULL,
    alarm_type VARCHAR(64) NOT NULL,
    confidence FLOAT,
    process_opinion TEXT,
    process_person INTEGER,  -- 处理人员ID
    process_status alarm_process_status NOT NULL DEFAULT 'unprocessed',
    process_feedback TEXT,
    image_url VARCHAR(1024) NOT NULL,
    device_ip VARCHAR(15) NOT NULL,
    user_code VARCHAR(64),  -- 允许为空（如报警暂未分配给用户时）
    create_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 外键约束（需确保t_device表已创建）
    CONSTRAINT fk_alarm_device FOREIGN KEY (device_ip) REFERENCES t_device (device_ip) 
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_alarm_user FOREIGN KEY (user_code) REFERENCES t_user (user_code)
    ON DELETE SET NULL  -- 用户表记录删除时，报警表的user_code设为NULL（避免数据丢失）
    ON UPDATE CASCADE   -- 用户ID更新时，报警表同步更新
);

-- 第三步：单独给字段添加注释（PostgreSQL标准写法）
COMMENT ON COLUMN t_alarm_info.alarm_time IS '报警发生时间';
COMMENT ON COLUMN t_alarm_info.longitude IS '报警位置经度';
COMMENT ON COLUMN t_alarm_info.latitude IS '报警位置纬度';
COMMENT ON COLUMN t_alarm_info.alarm_type IS '报警类型（如"越界报警""烟雾报警""设备异常"）';
COMMENT ON COLUMN t_alarm_info.process_opinion IS '处理意见';
COMMENT ON COLUMN t_alarm_info.process_person IS '处理人员姓名/工号';
COMMENT ON COLUMN t_alarm_info.process_status IS '处理状态';
COMMENT ON COLUMN t_alarm_info.process_feedback IS '处理结果反馈';
COMMENT ON COLUMN t_alarm_info.image_url IS '报警相关图片地址（多个地址用逗号分隔）';
COMMENT ON COLUMN t_alarm_info.device_ip IS '报警设备IP地址';
COMMENT ON COLUMN t_alarm_info.user_code IS '关联的用户编号（处理该报警的用户）';
COMMENT ON COLUMN t_alarm_info.create_time IS '报警记录创建时间';
COMMENT ON COLUMN t_alarm_info.update_time IS '报警记录更新时间';

-- 第四步：给表添加整体注释（可选）
COMMENT ON TABLE t_alarm_info IS '报警信息表';

-- 第五步：创建索引（保持不变）
CREATE INDEX idx_alarm_device_ip ON t_alarm_info (device_ip);
CREATE INDEX idx_alarm_user_code ON t_alarm_info (user_code);
CREATE INDEX idx_alarm_time ON t_alarm_info (alarm_time);
CREATE INDEX idx_alarm_process_status ON t_alarm_info (process_status);
CREATE INDEX idx_alarm_type ON t_alarm_info (alarm_type);