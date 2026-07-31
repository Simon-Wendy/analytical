# 创建基本信息表 tb_jober_base_info
# create table tb_jober_base_info(工号 varchar(50) not null, 姓名 varchar(100), 部门序列 varchar(50), 职务 varchar(50), 岗位类型 varchar(50), 是否离职 bit(1) comment "0 表示在职，1表示离职", primary key(工号)) engine = InnoDB default charset = 'utf8';



-- =====================================================
-- 数据库: db_salary_rzq
-- 描述: 薪资提成管理系统数据库
-- 创建日期: 2026-04-24
-- =====================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS rzq CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE rzq;

-- =====================================================
-- 表1: tb_department_base_info (部门基础信息表)
-- =====================================================
DROP TABLE IF EXISTS tb_department_base_info;
CREATE TABLE tb_department_base_info (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键ID',
    dept_seq VARCHAR(50) NOT NULL COMMENT '部门序列',
    company VARCHAR(100) NOT NULL COMMENT '公司',
    business_unit VARCHAR(100) COMMENT '事业部',
    first_level_dept VARCHAR(100) COMMENT '一级部门',
    second_level_dept VARCHAR(100) COMMENT '二级部门',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_dept_seq (dept_seq)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部门基础信息表';

-- =====================================================
-- 表2: tb_jober_base_info (员工基础信息表)
-- =====================================================
DROP TABLE IF EXISTS tb_jober_base_info;
CREATE TABLE tb_jober_base_info (
    emp_no VARCHAR(50) NOT null primary key COMMENT '工号',
    emp_name VARCHAR(50) NOT NULL COMMENT '姓名',
    dept_seq VARCHAR(50) COMMENT '部门序列',
    position VARCHAR(100) COMMENT '职务',
    job_category VARCHAR(50) COMMENT '岗位类别',
    is_resigned TINYINT DEFAULT 0 COMMENT '是否离职(0-在职,1-离职)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    unique KEY uk_emp_no(emp_no),
    INDEX idx_dept_seq (dept_seq),
    INDEX idx_emp_name (emp_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工基础信息表';

-- =====================================================
-- 表3: tb_jober_detail_info (员工详细信息表)
-- =====================================================
DROP TABLE IF EXISTS tb_jober_detail_info;
CREATE TABLE tb_jober_detail_info (
    emp_no VARCHAR(50) NOT NULL COMMENT '工号',
    id_card VARCHAR(18) COMMENT '身份证号',
    address VARCHAR(255) COMMENT '现住址',
    phone VARCHAR(20) COMMENT '手机号',
    entry_date DATE COMMENT '入职时间',
    gender TINYINT COMMENT '性别(0-女,1-男)',
    graduate_school VARCHAR(100) COMMENT '毕业学校',
    major varchar(100) comment '所学专业',
    registration_address varchar(255) comment '户籍地',
    graduate_date DATE COMMENT '毕业时间',
    resign_date DATE COMMENT '离职时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (emp_no),
    INDEX idx_phone (phone),
    FOREIGN KEY (emp_no) REFERENCES tb_jober_base_info(emp_no) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工详细信息表';

-- =====================================================
-- 表4: tb_rank_salary (职级薪资表)
-- =====================================================
DROP TABLE IF EXISTS tb_rank_salary;
CREATE TABLE tb_rank_salary (
    rank_id VARCHAR(50) NOT NULL COMMENT '职级ID',
    rank_name VARCHAR(50) NOT NULL COMMENT '职级',
    salary DECIMAL(15,2) COMMENT '工资',
    base_salary DECIMAL(15,2) COMMENT '基本工资',
    performance_salary DECIMAL(15,2) COMMENT '绩效工资',
    category VARCHAR(50) COMMENT '类别',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (rank_id),
    INDEX idx_rank_name (rank_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='职级薪资表';

-- =====================================================
-- 表5: tb_rank_salary_history (职级薪资历史表)
-- =====================================================
DROP TABLE IF EXISTS tb_rank_salary_history;
CREATE TABLE tb_rank_salary_history (
    id VARCHAR(100) NOT NULL PRIMARY KEY COMMENT 'ID：日期和工号合成，避免重复',
    record_date DATE NOT NULL COMMENT '日期',
    emp_no VARCHAR(50) NOT NULL COMMENT '工号',
    rank_id VARCHAR(50) COMMENT '职级ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_record_date (record_date),
    INDEX idx_emp_no (emp_no),
    INDEX idx_rank_id (rank_id),
    FOREIGN KEY (emp_no) REFERENCES tb_jober_base_info(emp_no) ON DELETE CASCADE,
    FOREIGN KEY (rank_id) REFERENCES tb_rank_salary(rank_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='职级薪资历史表';

-- =====================================================
-- 表6: tb_margins (毛利表)
-- =====================================================
DROP TABLE IF EXISTS tb_margins;
CREATE TABLE tb_margins (
    margin_no VARCHAR(50) NOT NULL COMMENT '利润编号',
    region VARCHAR(100) COMMENT '区域',
    category1 VARCHAR(100) COMMENT '分类1',
    category2 VARCHAR(100) COMMENT '分类2',
    category3 VARCHAR(100) COMMENT '分类3',
    product_name_fx VARCHAR(100) COMMENT '纷享销客产品名称',
    other_tags VARCHAR(255) COMMENT '其他标签',
    margin_actual_algo VARCHAR(255) COMMENT '毛利-实际算法',
    margin_performance_base_algo VARCHAR(255) COMMENT '毛利业绩基数算法标准处理',
    margin_commission_base_algo VARCHAR(255) COMMENT '毛利提成基数算法标准处理',
    product_cost DECIMAL(15,2) COMMENT '产品成本',
    sales_performance_coeff varchar(255) COMMENT '售卖业绩系数',
    margin_category VARCHAR(50) COMMENT '毛利分类',
    margin_rate_performance_base varchar(255) COMMENT '毛利率业绩基数',
    margin_rate_commission_base varchar(255) COMMENT '毛利率提成基数',
    member_standard_price DECIMAL(15,2) COMMENT '会员标准价格',
    margin_remarks TEXT COMMENT '毛利备注',
    remarks TEXT COMMENT '备注',
    internal_remarks TEXT COMMENT '内部备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (margin_no),
    INDEX idx_category (category2),
    INDEX idx_product_name (product_name_fx)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='毛利表';

-- =====================================================
-- 表7: tb_client_base (客户基础信息表)
-- =====================================================
DROP TABLE IF EXISTS tb_client_base;
CREATE TABLE tb_client_base (
    id varchar(255) not null PRIMARY KEY COMMENT 'ID,唯一识别信息',
    receipt_date DATE COMMENT '收款日期',
    account_id VARCHAR(50) COMMENT '账户ID',
    account_name VARCHAR(100) COMMENT '账户名称',
    client_name VARCHAR(100) COMMENT '客户名称',
    client_id VARCHAR(50) COMMENT '客户ID',
    first_industry VARCHAR(50) COMMENT '一级行业',
    second_industry VARCHAR(50) COMMENT '二级行业',
    product VARCHAR(100) COMMENT '产品',
    first_consume_date DATE COMMENT '首消日期',
    receipt_amount DECIMAL(15,2) COMMENT '收款金额',
    service_fee DECIMAL(15,2) COMMENT '服务费',
    prepayment_amount DECIMAL(15,2) COMMENT '预存款金额',
    platform VARCHAR(50) COMMENT '投放平台：百度独代、服务商、XHS、KS、TX、TT等',
    product_name_fx varchar(255) comment '产品名称',
    margin_no VARCHAR(50) COMMENT '利润编号',
    emp_no VARCHAR(50) COMMENT '工号',
    manager_no varchar(50) comment '经理工号',
    purchase_third decimal(20,4) comment '支出金额',
    flowgem DECIMAL(10,4) comment '流量宝金额',
    joint_no varchar(50) comment '甩单人工号',
    joint_manager_no varchar(50) comment '甩单人经理工号',
    remarks text comment '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (emp_no) REFERENCES tb_jober_base_info(emp_no) ON DELETE SET NULL,
    FOREIGN KEY (margin_no) REFERENCES tb_margins(margin_no) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户基础信息表';

-- =====================================================
-- 表8: tb_client_adver_info (客户投放信息表)
-- =====================================================
DROP TABLE IF EXISTS tb_client_adver_info;
CREATE TABLE tb_client_adver_info (
    ad_id VARCHAR(50) NOT null primary key COMMENT '投放ID',
    id varchar(255) COMMENT '客户唯一识别ID',
    ad_date DATE NOT NULL COMMENT '日期',
    account_name VARCHAR(100) COMMENT '账户名称',
    account_id VARCHAR(50) COMMENT '账户ID',
    ad_type VARCHAR(50) COMMENT '投放类型指：大搜消耗、服务商消耗、售卖产品、TTAD消耗、TT品牌消耗等',
    monthly_consumption DECIMAL(15,4) COMMENT '当月消耗',
    new_monthly_consumption decimal(15,4) comment '当月新单消耗：中小&客服 预存款内的消耗(26年3月)，专职客服是60天内的预存款消耗(26年2月)，大客销售指4个月12万内的消耗(26年3月)',
    non_new_monthly_consumption decimal(15,4) comment '当月非新单消耗',
    consumption_30d DECIMAL(15,4) COMMENT '上线30天内消耗',
    consumption_60d DECIMAL(15,4) COMMENT '上线60天内消耗',
    brand_consumption decimal(15,4) comment '品牌消耗',
    remarks TEXT COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    index idx_id(id),
    FOREIGN KEY (id) REFERENCES tb_client_base(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户投放信息表';

-- =====================================================
-- 表9: tb_charge_info (充值信息表)
-- =====================================================
DROP TABLE IF EXISTS tb_charge_info;
CREATE TABLE tb_charge_info (
    id VARCHAR(255) PRIMARY KEY COMMENT '日期和ID的合成',
    charge_date DATE NOT NULL COMMENT '日期',
    account_name VARCHAR(100) COMMENT '账户名称',
    account_id VARCHAR(50) COMMENT '账户ID',
    charge_platform VARCHAR(50) COMMENT '充值平台',
    company_name VARCHAR(100) COMMENT '公司名称',
    charge_amount DECIMAL(15,2) COMMENT '充值金额',
    product_name VARCHAR(100) COMMENT '产品名称',
    rebate_amount DECIMAL(15,2) COMMENT '返款金额',
    actual_charge_amount DECIMAL(15,2) COMMENT '实际充值金额',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='充值信息表';

-- =====================================================
-- 表10: tb_salary_detail (薪资明细表)
-- =====================================================
DROP TABLE IF EXISTS tb_salary_detail;
CREATE TABLE tb_salary_detail (
    ad_id VARCHAR(50) NOT NULL primary key COMMENT '投放ID',
    id varchar(255) not null comment '客户识别ID',
    ad_date date comment '提成核算时间',
    new_order_commission DECIMAL(15,2) COMMENT '新单提成',
    renewal_commission DECIMAL(15,2) COMMENT '续费提成',
    new_order_profit DECIMAL(15,2) COMMENT '新单利润',
    renewal_profit DECIMAL(15,2) COMMENT '续费利润',
    new_order_commission_rate DECIMAL(10,4) COMMENT '新单提成系数',
    opex_rate decimal(10,4) comment '一线服务提成系数',
    renewal_commission_rate DECIMAL(10,4) COMMENT '续费提成系数',
    margin_rate DECIMAL(10,4) COMMENT '毛利率',
    kpi_score decimal(10,4) comment '绩效分数',
    manage_quarterly_back_pay_renewal decimal(10,4) comment '经理季度补发续费提成',
	manager_quarterly_back_pay_new decimal(10,4) comment '经理季度补发新单提成,绩效系数差额提成',
	quarterly_back_pay_renewal decimal(10,4) comment '一线季度补发续费提成',
	quarterly_back_pay_new decimal(10,4) comment '一线季度补发新单提成，即绩效系数差额提成',
	manager_renewal_commission decimal(10,4) comment '经理续费提成',
	manager_new_commission decimal(10,4) comment '经理新单提成' ,
	manager_kpi decimal(10,4) comment '经理绩效分',
	is_loan tinyint default 0 COMMENT '是否借款(0-非借款,1-借款)',
	manager_renewal_commission_rate decimal(10,4) comment '经理续费提成系数',
	manager_new_order_commission_rate decimal(10,4) comment '经理新单提成系数',
	manager_opex_rate decimal(10,4) comment '经理服务费提成系数',
	rebate decimal(10,4) comment '返点信息',
    remarks text comment '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (id) REFERENCES tb_client_base(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资明细表';

-- =====================================================
-- 表11: tb_kpi (KPI考核表)
-- =====================================================
DROP TABLE IF EXISTS tb_kpi;
CREATE TABLE tb_kpi (
    id VARCHAR(255) PRIMARY KEY COMMENT '日期与工号、名称的结合',
    kpi_date DATE NOT NULL COMMENT '日期',
    dimension VARCHAR(20) COMMENT '维度指月度、季度考核',
    emp_no VARCHAR(50) NOT NULL COMMENT '工号',
    category VARCHAR(50) COMMENT '指业绩考核、团队管理、内部管理指标或学习发展',
    kpi_name VARCHAR(100) COMMENT '名称',
    weight DECIMAL(5,2) COMMENT '权重',
    description TEXT COMMENT '说明',
    details TEXT COMMENT '细则',
    score DECIMAL(5,2) COMMENT '评分',
    task_target DECIMAL(15,2) COMMENT '任务',
    completed DECIMAL(15,2) COMMENT '完成',
    completion_rate DECIMAL(10,4) COMMENT '完成率',
    completion_status TEXT COMMENT '完成情况',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_kpi_date (kpi_date),
    INDEX idx_emp_no (emp_no),
    INDEX idx_dimension (dimension),
    FOREIGN KEY (emp_no) REFERENCES tb_jober_base_info(emp_no) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='KPI考核表';

-- =====================================================
-- 添加表关系注释
-- =====================================================

/*
表关系说明:
1. tb_jober_base_info (员工基础信息表) - 核心表
   ├── tb_jober_detail_info (1:1) - 员工详细信息
   ├── tb_rank_salary_history (1:N) - 职级薪资历史
   ├── tb_client_base (1:N) - 客户基础信息 (通过emp_no关联)
   └── tb_kpi (1:N) - KPI考核

2. tb_rank_salary (职级薪资表)
   └── tb_rank_salary_history (1:N) - 职级薪资历史 (通过rank_id关联)

3. tb_margins (毛利表)
   └── tb_client_base (1:N) - 客户基础信息 (通过margin_no关联)

4. tb_client_base (客户基础信息表)
   ├── tb_client_adver_info (1:N) - 客户投放信息 (通过account_id关联)
   ├── tb_charge_info (1:N) - 充值信息 (通过account_id关联)
   └── tb_department_base_info (N:1) - 部门信息 (通过dept_seq关联,逻辑关联)

5. tb_client_adver_info (客户投放信息表)
   └── tb_salary_detail (1:1) - 薪资明细 (通过ad_id关联)
*/
