-- 先创建设备状态枚举类型（前置）
CREATE TYPE device_status AS ENUM ('online', 'offline', 'fault', 'maintenance');

-- 创建设备表（rtsp_urls改为JSONB存储数组）
CREATE TABLE t_device (
    device_id SERIAL PRIMARY KEY,
    device_code VARCHAR(64) NOT NULL UNIQUE,
    device_ip VARCHAR(15) NOT NULL UNIQUE,
    -- 改为JSONB，存储RTSP地址数组，如 ["rtsp://192.168.1.100/stream1", "rtsp://192.168.1.100/stream2"]
    rtsp_urls JSONB DEFAULT '[]'::JSONB,
    note TEXT,
    device_config JSONB,
    device_info JSONB,
    status device_status NOT NULL DEFAULT 'offline',
    create_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 添加注释
COMMENT ON TABLE t_device IS '设备信息表';
COMMENT ON COLUMN t_device.device_id IS '设备ID（主键）';
COMMENT ON COLUMN t_device.device_code IS '设备编号（唯一）';
COMMENT ON COLUMN t_device.device_ip IS '设备IP地址（IPv4，唯一）';
COMMENT ON COLUMN t_device.rtsp_urls IS 'RTSP流地址数组（JSON格式，支持多个地址）';
COMMENT ON COLUMN t_device.note IS '设备备注';
COMMENT ON COLUMN t_device.device_config IS '设备配置（JSON格式）';
COMMENT ON COLUMN t_device.device_info IS '设备信息（JSON格式）';
COMMENT ON COLUMN t_device.status IS '设备状态（online=在线，offline=离线，fault=故障，maintenance=维护）';
COMMENT ON COLUMN t_device.create_time IS '设备创建时间';
COMMENT ON COLUMN t_device.update_time IS '设备更新时间';

-- 索引优化（支持按RTSP地址查询设备）
CREATE INDEX idx_device_rtsp_urls ON t_device USING GIN (rtsp_urls);
CREATE INDEX idx_device_config ON t_device USING GIN (device_config);
CREATE INDEX idx_device_status ON t_device (status);