CREATE DATABASE kk_db
    WITH 
    OWNER = postgres  -- 数据库所有者，默认用超级用户postgres即可
    ENCODING = 'UTF8'  -- 编码格式，必须设为UTF8以支持中文
    LC_COLLATE = 'Chinese (Simplified)_China.936'  -- 中文排序规则
    LC_CTYPE = 'Chinese (Simplified)_China.936'  -- 中文字符分类规则
    TABLESPACE = pg_default  -- 表空间，默认即可
    CONNECTION LIMIT = -1;  -- 连接数限制，-1表示无限制

-- 给数据库添加注释（可选，增强可读性）
COMMENT ON DATABASE kk_db IS '报警设备管理数据库';