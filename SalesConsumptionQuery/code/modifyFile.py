import pymysql
import CONFIG
from pymysql import Error as pymysqlError  # 注意这里导入的是pymysql的Error异常类，而不是mysql-connector的Error类。
import datetime

class baseFileCol(object):
    def __init__(self):
        self.tb_department_base_info_cols = ['id', 'dept_seq', 'company', 'business_unit', 'first_level_dept',
                                             'second_level_dept', 'created_at', 'updated_at']  # 表1：部门基础表
        self.tb_jober_base_info_cols = ['emp_no', 'emp_name', 'dept_seq', 'position', 'job_category', 'is_resigned',
                                        'created_at', 'updated_at']  # 表2：员工基础表
        self.tb_jober_detail_info_cols = ['emp_no', 'id_card', 'address', 'phone', 'entry_date', 'gender',
                                          'graduate_school', 'major','graduate_date', 'resign_date', 'created_at',
                                          'updated_at']  # 表3:员工详细信息表
        self.tb_rank_salary_cols = ['rank_id', 'rank_name', 'salary', 'base_salary', 'performance_salary', 'created_at',
                                    'updated_at']  # 表4:职级薪资表
        self.tb_rank_salary_history_cols = ['id', 'record_date', 'emp_no', 'rank_id', 'created_at',
                                            'updated_at']  # 表5:职级薪资历史表
        self.tb_margins_cols = ['margin_no', 'region', 'category1', 'category2', 'category3', 'product_name_fx',
                                'other_tags', 'margin_actual_algo', 'margin_performance_base_algo',
                                'margin_commission_base_algo', 'product_cost', 'sales_performance_coeff',
                                'margin_category', 'margin_rate_performance_base', 'margin_rate_commission_base',
                                'member_standard_price', 'margin_remarks', 'remarks', 'internal_remarks', 'created_at',
                                'updated_at']  # 表6:毛利表
        self.tb_client_base_cols = ['id', 'receipt_date', 'account_id', 'account_name', 'client_name', 'client_id',
                                    'first_industry', 'second_industry', 'product', 'first_consume_date',
                                    'receipt_amount', 'service_fee', 'prepayment_amount', 'platform','product_name_fx' ,'margin_no',
                                    'emp_no','manager_no' ,'purchase_third', 'flowgem','joint_manager_no' ,'joint_no' ,'remarks', 'created_at',
                                    'updated_at']  # 表7:客户基础信息表
        self.tb_client_adver_info_cols = ['id', 'ad_id', 'ad_date', 'account_name', 'account_id', 'ad_type',
                                          'monthly_consumption','new_monthly_consumption' ,'consumption_30d','non_new_monthly_consumption' ,
                                          'consumption_60d', 'remarks', 'created_at', 'updated_at']  # 表8:客户投放信息表
        self.tb_charge_info_cols = ['id', 'charge_date DATE NOT NULL COMMENT', 'account_name', 'account_id',
                                    'charge_platform', 'company_name', 'charge_amount', 'product_name', 'rebate_amount',
                                    'actual_charge_amount', 'created_at', 'updated_at']  # 表9:充值信息表
        self.tb_salary_detail_cols = ['ad_id','id','ad_date' ,'new_order_commission', 'renewal_commission', 'new_order_profit',
                                      'renewal_profit', 'new_order_commission_rate', 'renewal_commission_rate',
                                      'margin_rate','kpi_score','manager_new_order_commission_rate','manager_renewal_commission_rate',
                                      'manager_kpi','manager_new_commission','manager_renewal_commission','quarterly_back_pay_new',
                                      'quarterly_back_pay_renewal','manager_quarterly_back_pay_new','manage_quarterly_back_pay_renewal','rebate',
                                      'remarks', 'created_at', 'updated_at']  # 表10:薪资明细表
        self.tb_kpi_cols = ['id', 'kpi_date', 'dimension', 'emp_no', 'category', 'kpi_name', 'weight', 'description',
                            'details', 'score', 'task_target', 'completed', 'completion_rate', 'completion_status',
                            'created_at', 'updated_at']  # 表11:KPI考核表


class modifyDataFile(object):
    def __init__(self):
        self.host = CONFIG.HOST_NAME
        self.name = CONFIG.USER_NAME
        self.pw = CONFIG.USER_PASSWORD
        self.db = CONFIG.DB_NAME

    def concation(self):  # 链接数据库
        connection = None
        try:
            connection = pymysql.connect(host=self.host, user=self.name, password=self.pw, database=self.db)
        except pymysqlError as e:
            print(f"The error '{e}' occurred")
        return connection

    def insertTbData(self, tb, columns, data,pk=False):
        '''
        tb 要插入的数据表名称
        columns 要插入的数据列名（必须在数据库中有对应的名称）
        data 需要插入的数据,元组形式(1,2)
        pk 主键名称
        '''
        con = self.concation()
        cols = [x for x in columns if x not in [pk]]
        updateCols = ''
        for col in cols:
            if cols.index(col) != 0:
                updateCols += ','
            updateCols += col + '=' + 'VALUES({})'.format(col)
        placeholders = ', '.join(['%s'] * len(data))  # 生成占位符
        place_col_holders = ', '.join(columns)
        query = 'INSERT INTO {}({}) VALUES({}) ON DUPLICATE KEY UPDATE {};'.format(tb, place_col_holders, placeholders,
                                                                                   updateCols)
        try:
            with con.cursor() as cursor:
                cursor.execute(query, data) #执行单条插入
                # cursor.executemany(query, data) #执行多条插入
            con.commit()
        except pymysqlError as e:
            with open(r'../data/error.txt', 'a') as f:
                f.write(f"The error '{e}' occurred. Time:{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}; \n error query:{query}; data:{str(data)}. \n")
            print('Error :', e)
            con.rollback()
