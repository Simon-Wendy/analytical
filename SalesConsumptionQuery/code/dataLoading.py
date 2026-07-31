import pandas as pd, numpy as np
import pypinyin  # 将汉字转换成拼音
from pypinyin import lazy_pinyin, Style
import openpyxl
import re

import CONFIG
from modifyFile import modifyDataFile,baseFileCol

import datetime
import warnings
warnings.filterwarnings('ignore')

# 汉字转成拼音
class chinaToLetter(object): #将汉字转成成拼音形式的字母
    def __init__(self):
        pass
    def modeKey(self, text):  # 将汉字转换成拼音
        text = str(text)
        if len(text) < 1: #将空字符转换成NULL
            text = 'NULL'
        py = lazy_pinyin(text, style=Style.NORMAL)  # 将汉字转换成字母
        tx = ''.join(py)  # 将小写字母转换成大写
        return tx.upper()

# 员工基础信息表
class baseInfoForm(object):
    def __init__(self):
        tbname = baseFileCol()
        self.updata = modifyDataFile()
        self.path = CONFIG.client_base #数据地址
        self.department_base_info_cols = tbname.tb_department_base_info_cols  # 部门基础信息表头
        self.jober_base_info_cols = tbname.tb_jober_base_info_cols  # 员工基础信息表头
        self.jober_detail_info_cols = tbname.tb_jober_detail_info_cols  # 员工详细信息表头

    def is_date(self,value): # 检测是否是日期格式
        '''
        用途： 用于检测值是否是函数
        value: 需要检测的值
        return： 返回日期或NULL
        '''
        try:
            return pd.to_datetime(value)
        except(ValueError, TypeError):
            if re.findall(r'^\d{4}/\d{1,2}',str(value)):
                if re.findall(r'^\d{4}/\d{1,2}/\d{1,2}',str(value)):
                    tmp = re.findall(r'^\d{4}/\d{1,2}/\d{1,2}',str(value))[0]
                else:
                    tmp = re.findall(r'^\d{4}/\d{1,2}',str(value))[0] +'/01'
            else:
                tmp = np.nan
            return tmp

    def readFile(self):#读取文件内所有表信息
        '''
        读取员工信息，包括在职人员和离职人员
        return: 分别返回在职人员和离职人员信息
        '''
        wb = openpyxl.load_workbook(self.path) #加载Excel
        sheet_names = wb.sheetnames #读取所有sheet名称
        employed = pd.DataFrame()
        unemployed = pd.DataFrame()
        columns = {'公司':'company', '一级部门':'business_unit', '二级部门':'first_level_dept', '部门':'second_level_dept',
                   '员工编号':'emp_no', '姓名':'emp_name', '职务':'position', '岗位':'job_category','入职时间':'entry_date',
                   '性别':'gender', '身份证号':'id_card', '毕业院校':'graduate_school', '毕业时间':'graduate_date',
                   '所学专业':'major', '个人手机号':'phone','邮箱':'email','户籍地址':'registration_address','现住址':'address'}
        for sheet_name in sheet_names:
            if ('网络+思创在职' == sheet_name)|('独立业务' == sheet_name):
                df = pd.read_excel(self.path,sheet_name=sheet_name,header=2)
                if '工号' in df.columns:
                    df = df.rename(columns = {'工号':"员工编号"})
                employed = pd.concat([employed,df])
            if '普特在职' == sheet_name:
                df = pd.read_excel(self.path,sheet_name=sheet_name)
                employed = pd.concat([employed,df])
            if '完美在职' == sheet_name:
                df = pd.read_excel(self.path,sheet_name=sheet_name,header=1)
                employed = pd.concat([employed,df])
            if '离职' in sheet_name: # 读取离职人员信息
                n = 2
                if '完美离职' == sheet_name: # 完美表头有差异，需要单独处理
                    n = 0
                df = pd.read_excel(self.path,sheet_name=sheet_name,header=n)
                if '离职时间' in df.columns:
                    df = df.rename(columns={'离职时间':'resign_date'})
                unemployed = pd.concat([unemployed,df])
        unemployed = unemployed.rename(columns=columns) #修改离职人员列名称保持一致
        unemployed['is_resigned'] = 1 # 离职人员信息
        employed = employed.rename(columns=columns) #修改列名称，与数据库名称保持一致
        employed['is_resigned'] = 0
        return employed,unemployed
    def updateDepartmentBaseInfo(self,data):         # 载入部门数据，补充部门序列
        cols = ['company', 'business_unit', 'first_level_dept', 'second_level_dept'] #主要的四个列名
        department_base = data[cols].drop_duplicates().reset_index(drop=True) #删除重复项保留唯一值
        query = 'select dept_seq,company,business_unit,first_level_dept,second_level_dept from tb_department_base_info;' #查询数据库中数据语句
        department_base_norm = pd.read_sql(query, con=self.updata.concation()) #读取数据库中数据
        tmp_drop = department_base[department_base.apply(tuple,axis=1).isin(department_base_norm[cols].apply(tuple,axis=1))].index.tolist() #需要删除的重复值的index
        tmps = department_base.drop(tmp_drop).reset_index(drop=True)
        max_index = np.max(department_base_norm['dept_seq'].astype(int)) #获取存储的最大序列

        if len(tmps) != 0: # 判断新的需要插入的数据
            tmps['dept_seq'] = tmps.index + max_index + 1
            cols = [x for x in self.department_base_info_cols if x in tmps.columns]
            for idx in range(len(tmps)):
                tmp = tmps[cols].iloc[idx].values
                value = tuple(tmp)
                self.updata.insertTbData('tb_department_base_info', cols, value) #更新数据表

    def uploadData(self,data): #录入员工基础表和相信信息表
        #读取部门唯一序列
        query = 'select dept_seq,company,business_unit,first_level_dept,second_level_dept from tb_department_base_info;'
        department_base = pd.read_sql(query,con=self.updata.concation())

        details_data = pd.merge(data,department_base,on=['company', 'business_unit', 'first_level_dept','second_level_dept'],how='left') #将部门序列合并在基础表中
        details_data['gender'] = details_data['gender'].map(lambda x: 0 if x=="女" else 1) #将文字转换成0-1形式
        details_data['graduate_date'] = details_data['graduate_date'].map(lambda x: self.is_date(x))
        if 'resign_date' in details_data.columns: #判断是否为离职数据，检查并清洗离职数据
            details_data['resign_date'] = details_data['resign_date'].map(lambda x: self.is_date(x))

        # 更新数据至数据库
        for idx in range(len(details_data)):
            tmp = details_data.iloc[idx].dropna()
            baseCol = [x for x in self.jober_base_info_cols if x in tmp.index.tolist()]
            detailsCols = [x for x in self.jober_detail_info_cols if x in tmp.index.tolist()]
            self.updata.insertTbData('tb_jober_base_info', baseCol,tuple(tmp[baseCol].values),'emp_no') #插入基础员工数据
            self.updata.insertTbData('tb_jober_detail_info', detailsCols,tuple(tmp[detailsCols].values),'emp_no') #插入详细员工数据

    def go(self):
        employed,unemployed = self.readFile()
        self.updateDepartmentBaseInfo(unemployed) #更新离职人员部门信息表
        self.updateDepartmentBaseInfo(employed) #更新部门基础信息表
        self.uploadData(unemployed) #更新离职人员信息
        self.uploadData(employed) #更新录入员工信息

# 利润信息表
class margins(object): # 插入和更新利润对应表
    def __init__(self):
        self.path = CONFIG.margins
        self.cols = baseFileCol().tb_margins_cols
        self.load = modifyDataFile()
        self.columns = {'产品编号': 'margin_no', '区域': 'region', '分类1': 'category1', '分类2': 'category2',
                   '分类3': 'category3', '销客产品名称': 'product_name_fx',
                   '其他标签': 'other_tags', '毛利-实际算法': 'margin_actual_algo',
                   '毛利业绩基数算法-标准处理': 'margin_performance_base_algo',
                   '毛利提成基数算法-标准处理': 'margin_commission_base_algo', '产品成本': 'product_cost',
                   '售卖业绩系数-标准处理': 'sales_performance_coeff',
                   '毛利分类': 'margin_category', '毛利率-业绩基数': 'margin_rate_performance_base',
                   '毛利率-提成基数': 'margin_rate_commission_base',
                   '会员标准价格': 'member_standard_price', '毛利备注': 'margin_remarks', '备注': 'remarks',
                   '内部备注': 'internal_remarks'}
    def readFile(self):

        df = pd.read_excel(self.path,sheet_name='产品毛利对应表')
        df = df.rename(columns = self.columns)
        return df
    def upLoadData(self,data):
        for idx in range(len(data)):
            tmp = data.iloc[idx].dropna()
            col = [x for x in self.cols if x in tmp.index.tolist()]
            self.load.insertTbData('tb_margins', col,tuple(tmp[col].values),'margin_no')

    def go(self):
        data = self.readFile()
        self.upLoadData(data)

# 基础信息表
class basicInfo(object):
    def __init__(self):
        self.employ_sql = '''select tdbi.second_level_dept,tjbi.emp_name,tjbi.emp_no from tb_jober_base_info tjbi left join tb_department_base_info tdbi 
        on tjbi.dept_seq=tdbi.dept_seq where tjbi.is_resigned =0;''' #读取在职员工信息
        self.margins_sql = '''select margin_no,product_name_fx from tb_margins;''' #读取产品利润信息

# KA产品售卖提成
class productCommission(object): #KA产品提成信息导入
    def __init__(self):
        self.basic = basicInfo() #基础信息表
        self.con = modifyDataFile().concation() # 链接数据库
        self.path = CONFIG.product_commission_path
        self.data_refresh = modifyDataFile()
        self.client_base_cols = baseFileCol().tb_client_base_cols #基础客户信息表头
        self.salary_detail_cols = baseFileCol().tb_salary_detail_cols # 提成信息明细
        self.client_ad_cols = baseFileCol().tb_client_adver_info_cols # 广告投放明细

    def readFile(self): #读取数据
        data = pd.DataFrame()
        for path in self.path:
            for key,value in path.items():
                df = pd.read_excel(value,sheet_name="产品汇总")
                df['ad_date'] = key
                data = pd.concat([data,df],ignore_index=True)
        return data
    def collateData(self,data):
        sql = 'select margin_no,product_name_fx from tb_margins;'
        margins_no = pd.read_sql(sql,con=self.con)
        cols = {'销售订单编号':'id', '收款审核日期':'receipt_date', '账户ID':'account_id', '账户名称':'account_name', '公司名称':'client_name',
                '总认款金额':'receipt_amount','产品认款金额':'prepayment_amount', '服务费(产品溢价+非大搜服务费)':'service_fee',
                '业绩核算时间':'first_consume_date', '提单人工号':'emp_no', '经理工号':'manager_no','关联核算工号':'joint_no',
                '关联核算经理工号':'joint_manager_no', '特殊情况备注':'remarks', '纷享销客产品名称':'product_name_fx', '支出金额':'purchase_third',
                '利润率':'','流量宝/加油包金额':'flowgem', '利润':'new_order_profit', '一线利润系数':'new_order_commission_rate',
                '一线提成':'new_order_commission', '经理系数':'manager_new_order_commission_rate','经理提成':'manager_new_commission',
                '一线绩效':'kpi_score','一线季度补发':'quarterly_back_pay_new','经理绩效':'manager_kpi','经理季度补发':'manager_quarterly_back_pay_new',
                '是否账期':'is_loan'}
        data['platform'] = '产品售卖'
        data['是否账期'] = data['是否账期'].map(lambda x: 1 if x == '是' else 0)
        for col in data.columns.tolist():
            if re.findall('总认款金额',col):
                data.rename(columns ={col:'总认款金额'},inplace=True)
        data = data.rename(columns = cols)
        data['id'] = data['id'] +'_'+ data.index.astype(str)
        data['ad_id'] = data['ad_date'].map(lambda x: datetime.datetime.strftime(pd.to_datetime(x), '%Y%m%d')) + '_' + data['id']
        data = pd.merge(data,margins_no,on='product_name_fx',how='left').reset_index(drop=True)

        return data
    def uploadData(self,data):
        for idx in range(len(data)):
            tmp = data.iloc[idx].dropna()
            base_col = [x for x in self.client_base_cols if x in tmp.index.tolist()] #基础客户信息表头
            detail_col = [x for x in self.salary_detail_cols if x in tmp.index.tolist()] #详细提成信息表头
            self.data_refresh.insertTbData('tb_client_base',base_col,tuple(tmp[base_col].values),'id')
            self.data_refresh.insertTbData('tb_salary_detail',detail_col,tuple(tmp[detail_col].values),'ad_id')

    def go(self):
        data = self.readFile()
        data = self.collateData(data)
        self.uploadData(data)

#KA搜索消耗提成
class kaSearchConsumption(object):
    def __init__(self):
        self.basic_sql = basicInfo().employ_sql
        self.pathList = CONFIG.ka_search_con_path
        self.topinyin = chinaToLetter()
        self.client_adver_cols = baseFileCol().tb_client_adver_info_cols
        self.salary_detail_cols = baseFileCol().tb_salary_detail_cols
        self.data_refresh = modifyDataFile()
        self.client_base_cols = baseFileCol().tb_client_base_cols
        self.con = modifyDataFile().concation()
    def readFile(self,eva = False): # 读取本地文件
        data = pd.DataFrame()
        for paths in self.pathList:
            for key,value in paths.items():
                df1 = pd.read_excel(value,sheet_name='新户提成')
                df2 = pd.read_excel(value,sheet_name='老户提成')
                if eva:
                    coefficient = pd.read_excel(value,sheet_name='绩效得分&利润系数')[['工号','新单提成区间']]
                    df1 = pd.merge(df1,coefficient,on='工号',how='left')
                data = pd.concat([data,df1,df2],ignore_index=True)
                data['ad_date'] = key

        return data
    def employNo(self,name):
        '''
        name:需要匹配的员工姓名
        return: 返回对应员工的工号
        '''
        if name in ['NULL',np.nan,'nan','null','-']:
            return np.nan
        employInfo = pd.read_sql(self.basic_sql,con=self.con)
        emp_no = employInfo[employInfo['emp_name']==name]['emp_no'].values
        if len(emp_no)>0:
            res = emp_no[0]
            return res
        else:
            return np.nan

    def collateData(self,data): # 修正数据类型，清洗脏数据
        # 读取数据的表头，按照表头一一对应名称
        cols = {'回款时间':'receipt_date','工号':'emp_no', '收款金额':'receipt_amount', '服务费':'service_fee', '客户名称':'client_name',
                '账户名':'account_name','产品':'product','账户首次消费日':'first_consume_date', '品牌类合计消费':'brand_consumption',
                '新单利润(含服务费)':'new_order_profit', '续费利润':'renewal_profit', '新单提成区间':'new_order_commission_rate',
                '新单消费提成':'new_order_commission', '销售续费提成系数':'renewal_commission_rate', '绩效得分':'kpi_score',
                '续费提成':'renewal_commission','经理工号':'manager_no', '团队绩效分数':'manager_kpi',
                '经理新单提成系数':'manager_new_order_commission_rate', '经理新单团队提成':'manager_new_commission',
                '经理续费提成系数':'manager_renewal_commission_rate','经理续费提成':'manager_renewal_commission', '账期':'is_loan',
                'MEG账户一级行业_新_':'first_industry', 'MEG账户二级行业_新_':'second_industry','季度新单补发差额':'quarterly_back_pay_new',
                '经理季度补发':'manager_quarterly_back_pay_new','季度续费补发差额':'quarterly_back_pay_renewal',
                '经理季度续费补发':'manage_quarterly_back_pay_renewal'}
        data['product_name_fx'] = '搜索推广'
        data['margin_no'] = '20251128V005'
        data['prepayment_amount'] = data['收款金额'] - data['服务费']
        data['platform'] = '百度独代'
        data['ad_type'] = '大搜消耗'
        data['monthly_consumption'] = data['大搜消费'] + data['信息流消费']

        data['joint_no'] = data['中小甩单销售'].map(lambda x:self.employNo(x))
        data['joint_manager_no'] = data['中小经理'].map(lambda x:self.employNo(x))
        data['remarks'] = data['备注1'] + '; '+data['备注1.1']
        data['id'] = data['订单编号'] + '_' + data['账户名'].map(lambda x:self.topinyin.modeKey(x))
        data['ad_id'] = data['ad_date'].map(lambda x:datetime.datetime.strftime(pd.to_datetime(x),'%Y%m%d')) + '_' + data['id']
        data = data.rename(columns = cols)
        # 需要判断消耗大于0的客户或者有利润或有提成的客户
        data = data.loc[(data['monthly_consumption'] != 0) | (data['new_order_profit'] != 0) | (
                    data['renewal_profit'] != 0)].reset_index(drop=True)

        return data

    def uploadData(self,data): # 将数据导入数据库
        for idx in range(len(data)):
            tmp = data.iloc[idx].dropna()
            basic_col = [x for x in self.client_base_cols if x in tmp.index.tolist()] # 基础客户信息表头
            adver_col = [x for x in self.client_adver_cols if x in tmp.index.tolist()] # 客户广告投放信息表头
            commission_col = [x for x in self.salary_detail_cols if x in tmp.index.tolist()] # 基本提成信息表头
            self.data_refresh.insertTbData('tb_client_base',basic_col,tuple(tmp[basic_col].values),'id')
            self.data_refresh.insertTbData('tb_client_adver_info',adver_col,tuple(tmp[adver_col].values),'ad_id')
            self.data_refresh.insertTbData('tb_salary_detail',commission_col,tuple(tmp[commission_col].values),'ad_id')

    def go(self):
        data = self.readFile()
        data = self.collateData(data)
        self.uploadData(data)

#XHS提成信息
class xhsConsumption(object):
    def __init__(self):
        self.pathList = CONFIG.xhs_con_path #XHS提成文件路径
        self.topinyin = chinaToLetter() #汉字转拼音
        self.employNo = kaSearchConsumption() #员工信息
        self.data_refresh = modifyDataFile() # 数据库更新

    def readFile(self):
        data = pd.DataFrame
        for paths in self.pathList:
            for key,path in paths.items():
                df1 = pd.read_excel(path,sheet_name='专职').rename(columns={'首消60天内消耗':'当月新单消耗',})
                df2 = pd.read_excel(path,sheet_name='兼职').rename(columns={'一线提成系数':'销售新单系数','一线运营系数':'销售运营系数','经理提成':'经理新单提成'})
                df3 = pd.read_excel(path,sheet_name='大客')
                data = pd.concat([df1,df2,df3],ignore_index=True,axis=0)
                data['ad_date'] = key
        return data
    # 按照平台类型转换对应毛利编码
    def getjoberNo(self,name):
        '''
        name: 输入的平台类型，平台新客、非新客、存量等
        return: 返回对应人员工号信息
        '''
        # category = '20251128V329'
        if name == '平台新客':
            return '20251128V329'
        else:
            return '20251128V330'

    def collateData(self,data):
        margins_key = {'平台新客':'20251128V329'}
        cols = {'客户名称':'client_name', '子账号名称':'account_name', '到款日期':'receipt_date','提单人工号':'emp_no',
                '部门经理工号':'manager_no', '到款金额':'receipt_amount', '账户服务费':'service_fee', '总预存款':'prepayment_amount',
                '产品名称':'product_name_fx','首消日期':'first_consume_date','关联人工号':'joint_no','上线30天竞价现金消耗':'consumption_30d',
                '上线60天竞价现金消耗':'consumption_60d', '上线6个自然月在当月消耗':'monthly_consumption','是否账期':'is_loan',
                '当月新单消耗':'new_monthly_consumption', '续费消耗':'non_new_monthly_consumption', '销售新单系数':'new_order_commission_rate',
                '销售运营系数':'opex_rate', '销售续费系数':'renewal_commission_rate', '销售新单提成':'new_order_commission',
                '销售续费提成':'renewal_commission','经理新单系数':'manager_new_order_commission_rate', '经理运营系数':'manager_opex_rate',
                '经理续费系数':'manager_renewal_commission_rate', '经理新单提成':'manager_new_commission', '经理续费提成':'manager_renewal_commission',
                '新单预存款利润':'new_order_profit', '续费利润':'renewal_profit','客开识别类型':'ad_type','销售季度绩效':'kpi_score',
                '销售季度差额新单':'quarterly_back_pay_new','销售季度差额续费':'quarterly_back_pay_renewal','经理季度绩效':'manager_kpi',
                '经理季度差额新单':'manager_quarterly_back_pay_new','经理季度差额续费':'manage_quarterly_back_pay_renewal'}
        data['platform'] = 'XHS投流'
        data['pinyin'] = data['客户名称'].map(lambda x:self.topinyin.modeKey(x))
        data['pinyin2'] = data['子账号名称'].map(lambda x:self.topinyin.modeKey(x))
        data['remarks'] = data['REMARKS'] + '; ' + data['备注']
        # 替换销售订单编号，变换成时间+公司名称
        for idx in range(len(data)):
            if data.at[idx,'销售订单编号'] in ['NULL',np.nan,'-']:
                data.at[idx,'id'] = datetime.datetime.strftime(pd.to_datetime(data.at[idx,'核算业绩月份']),'%Y%m%d') + '_' + data.at[idx,'pinyin']
            else:
                data.at[idx,'id'] = data.at[idx,'销售订单编号'] + '_' + data.at[idx,'pinyin2']

            if data.at[idx,'提单人工号'] in ['NULL',np.nan,'-',0,'0']:
                name = data.at[idx,'提单人']
                emp = self.employNo.employNo(name)
                data.at[idx,'提单人工号'] = emp
            if data.at[idx, '部门经理工号'] in ['NULL', np.nan, '-', 0, '0']:
                data.at[idx, '部门经理工号'] = self.employNo.employNo(data.at[idx, '部门经理'])

        data = data.rename(columns = cols)
        data['receipt_date'] = data['receipt_date'].map(lambda x:np.nan if x in ['NULL',np.nan,'-'] else x)
        data['first_consume_date'] = data['first_consume_date'].map(lambda x:np.nan if x in ['NULL',np.nan,'-'] else x)
        data['margin_no'] = data['ad_type'].map(lambda x: '20251128V329' if x =='平台新客' else '20251128V330')
        data['is_loan'] = data['is_loan'].map(lambda x:1 if x =='是' else 0)
        data['joint_manager_no'] = data['甩单人经理'].map(lambda x:self.employNo.employNo(x))
        data['ad_id'] = data['ad_date'].map(lambda x:datetime.datetime.strftime(pd.to_datetime(x),'%Y%m%d')) + '_' + data['id']
        # print(data.columns,'\n','='*60)
        # print(data.head(),'\n','='*60)

        # 筛选有消耗或有提成的客户
        # data = data.loc[(data['new_monthly_consumption'] != 0) |(data['non_new_monthly_consumption'] !=0) | (data['new_order_commission'] !=0) | (data['renewal_commission'] !=0)].reset_index(drop=True)

        return data

    def uploadData(self,data):
        for idx in range(len(data)):
            tmp = data.iloc[idx,:].dropna()
            basic_client_col = [x for x in self.employNo.client_base_cols if x in tmp.index.tolist()]
            client_ad_col = [x for x in self.employNo.client_adver_cols if x in tmp.index.tolist()]
            commission_col = [x for x in self.employNo.salary_detail_cols if x in tmp.index.tolist()]
            self.data_refresh.insertTbData('tb_client_base',basic_client_col,tuple(tmp[basic_client_col].values.tolist()),'id')
            if 'monthly_consumption' in client_ad_col and tmp['monthly_consumption'] !=0 : # 过滤掉当月0消耗的客户信息
                    self.data_refresh.insertTbData('tb_client_adver_info',client_ad_col,tuple(tmp[client_ad_col].values.tolist()),'ad_id')
            self.data_refresh.insertTbData('tb_salary_detail',commission_col,tuple(tmp[commission_col].values.tolist()),'ad_id')

    def go(self):
        data = self.readFile()
        data = self.collateData(data)
        self.uploadData(data)

#服务商提成信息
class contractor(object):
    def __init__(self):
        self.paths = CONFIG.contractor_paths # 数据路径
        self.base_client_cols = baseFileCol().tb_client_base_cols #基础客户信息表头
        self.client_adver_cols = baseFileCol().tb_client_adver_info_cols # 客户广告投放信息表头
        self.salary_detail_cols = baseFileCol().tb_salary_detail_cols # 客户提成信息表头
        self.data_refresh = modifyDataFile()
        self.columns = {'收款审核日期':'receipt_date', '账户ID':'account_id', '账户名称':"account_name", '公司名称':'client_name',
                        '总认款金额\n（含服务费）':'receipt_amount', '产品\n认款金额':'prepayment_amount','服务费(产品溢价+非大搜服务费)':'service_fee',
                        '售卖产品':'product', '提单人工号':'emp_no', '经理工号':'manager_no',
                        '关联核算\n工号':'joint_no', '关联核算\n经理工号':'joint_manager_no','最早首消日':'first_consume_date',
                        'MEG客户一级行业（新）':'first_industry', 'MEG客户二级行业（新）':'second_industry', '备注':'remarks',
                        '总毛利':'new_order_profit', '一线系数':'new_order_commission_rate','一线提成':'new_order_commission',
                        '经理系数':'manager_new_order_commission_rate', '经理提成':'manager_new_commission',
                        '季度一线绩效':'kpi_score','季度一线差额':'quarterly_back_pay_new', '经理季度绩效':'manager_kpi',
                        '季度经理差额':'manager_quarterly_back_pay_new'}

    def readFile(self):
        for path_list in self.paths:
            for key,path in path_list.items():
                data = pd.read_excel(path,sheet_name=1)
                data['ad_date'] = key
                return data
    def collateData(self,data):
        for col in data.columns:
            if re.findall('总现金',col):
                data.rename(columns={col:'总现金'},inplace=True)
                # print('1',col)
            if re.findall('通用词时效品专现金',col):
                data.rename(columns={col:'通用词时效品专现金'},inplace=True)
                # print('2',col)
            if re.findall('健康内容服务营销现金',col):
                data.rename(columns={col:'健康内容服务营销现金'},inplace=True)
                # print('3',col)
            if re.findall('丝路现金',col):
                data.rename(columns={col:'丝路现金'},inplace=True)
                # print('4',col)
            if re.findall('行业标签',col):
                data.rename(columns={col:'行业标签'},inplace=True)
                # print('5',col)
            if re.findall('消耗',col):
                data.rename(columns={col:'总消耗'},inplace=True)
                # print('6',col)
        data['brand_consumption'] = data['通用词时效品专现金'] + data['健康内容服务营销现金'] + data['百+内容加热现金']
        data['monthly_consumption'] = 0
        # 判断售卖产品中非推广消耗客户品牌消耗改为0
        for i in range(len(data)):
            if re.findall('推广',data.at[i,'售卖产品']):
                data.at[i,'monthly_consumption'] = data.at[i,'总现金'] - data.at[i,'brand_consumption']
            else:
                data.at[i,'monthly_consumption'] = data.at[i,'brand_consumption']

        data['id'] = data['转款月份'].map(lambda x:datetime.datetime.strftime(pd.to_datetime(x),'%Y%m%d') if pd.notna(x) else 'NULL') + data['账户名称'].map(lambda x:chinaToLetter().modeKey(x)) + data['总认款金额\n（含服务费）'].astype(str)
        data['ad_id'] = data['ad_date'].map(lambda x:datetime.datetime.strftime(pd.to_datetime(x),'%Y%m%d')) + data['id'] + '_' + data.index.astype(str)

        data['margin_no'] = data['行业标签'].map(lambda x:self.tag_mapping(x)) #将标签转换成对应的对应的利润编号
        data = data.rename(columns=self.columns)
        data['platform'] = '服务商'
        data['ad_type'] = '服务商消耗'
        data['manager_no'] = data['经理.1'].map(lambda x:kaSearchConsumption().employNo(x))

        return data

    def tag_mapping(self,x):
        tag_ = {'医疗医美':'20251128V007','非医疗医美-一类':'20251128V480','非医疗医美-二类':'20251128V013'}
        try:
            return tag_[x]
        except Exception as e:
            print('The conversion is error.\n',x,e)
            return x

    def uploadData(self,data):
        for i in range(len(data)):
            tmp = data.iloc[i,:].dropna()
            cols = tmp.index.tolist()
            client_col = [c for c in self.base_client_cols if c in cols]
            client_adv_col = [c for c in self.client_adver_cols if c in cols]
            salary_col = [c for c in self.salary_detail_cols if c in cols]
            # print('-'*300)
            # print(tmp.index.tolist(),'\n')
            # print(tmp.values.tolist())
            self.data_refresh.insertTbData('tb_client_base',client_col,tuple(tmp[client_col].values.tolist()),'id')
            # 过滤掉消耗为0的客户信息
            if 'monthly_consumption' in client_adv_col and tmp['monthly_consumption'] !=0:
                self.data_refresh.insertTbData('tb_client_adver_info',client_adv_col,tuple(tmp[client_adv_col].values.tolist()),'ad_id')
            self.data_refresh.insertTbData('tb_salary_detail',salary_col,tuple(tmp[salary_col].values.tolist()),'ad_id')
    def go(self):
        data = self.readFile()
        data = self.collateData(data)
        self.uploadData(data)

#TT提成信息
class ttConsumption(object):
    def __init__(self):
        self.paths = CONFIG.tt_paths  # 数据路径
        self.base_client_cols = baseFileCol().tb_client_base_cols  # 基础客户信息表头
        self.client_adver_cols = baseFileCol().tb_client_adver_info_cols  # 客户广告投放信息表头
        self.salary_detail_cols = baseFileCol().tb_salary_detail_cols  # 客户提成信息表头
        self.data_refresh = modifyDataFile()
        self.columns = {'工号':'emp_no', '签单金额':'receipt_amount', '预存款金额':'prepayment_amount', '服务费':'service_fee',
                        '公司名称':'client_name', '业务线':'platform','产品线':'product', '到款时间':'receipt_date',
                        '首消时间':'first_consume_date', '上线180内在本月消耗':'monthly_consumption',
                        '上线30天内消耗':'consumption_30d','毛利系数':'margin_rate', '毛利':'new_order_profit','返点':'rebate',
                        '提成系数':'new_order_commission_rate', '一线提成':'new_order_commission', '季度绩效':'kpi_score',
                        '一线季度差额提成':'quarterly_back_pay_new', '经理工号':'manager_no', '经理提成系数':'manager_new_order_commission_rate',
                        '经理新单提成':'manager_new_commission', '经理绩效':'manager_kpi', '经理季度差额提成':'manager_quarterly_back_pay_new'}
    @classmethod
    def margin_conversion(cls,column=None):
        '''
        此函数功能是从数据库中提取出需要字段的毛利标签
        column :需要对应转换的列名
        margin_no:产品编号和product_name_fx:纷享销客产品名称 默认附带
        '''
        con = modifyDataFile().concation()
        s = '''SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'rzq' AND TABLE_NAME = 'tb_margins';'''
        cols = pd.read_sql(s,con).values.tolist()
        if column is not None:
            if column in cols:
                col = column
            else:
                col = margins().columns[column]
            sql = f'''select {col},product_name_fx,margin_no from tb_margins;'''
            return pd.read_sql(sql, con=con)

        sql = '''select product_name_fx,margin_no from tb_margins;'''
        return pd.read_sql(sql,con=con)

    def readFile(self):
        for path_list in self.paths:
            for key,path in path_list.items():
                tmp1 = pd.read_excel(path,sheet_name='中小&客服').rename(columns={'销售提成':'一线提成'})
                tmp2 = pd.read_excel(path,sheet_name='大客')
                tmp3 = pd.read_excel(path,sheet_name='服务费提成').rename(columns={'一线提成点数':'提成系数','经理提成点数':'经理提成系数','经理提成':'经理新单提成'})
                tmp3['业务线'] = 'TT'
                tmp3['产品线'] = '服务费'
                print(tmp3.columns)
                data = pd.concat([tmp1,tmp2,tmp3],axis=0).reset_index(drop=True)
                print(data.columns)
                data['ad_date'] = key
                return data

    def collateData(self,data):
        # 整理数据对应利润标签
        data.rename(columns={'ID':'account_id'},inplace=True)
        data = data.sort_values(by=['公司名称','上线180内在本月消耗'],ascending=False).reset_index(drop=True)
        data['new_monthly_consumption'] = data['上线180内在本月消耗']
        tmps = data.groupby(by=['公司名称'])['产品线'].count().reset_index().rename(columns={'产品线':'count'})
        data = pd.merge(data,tmps,on='公司名称',how='left')
        data['product_name_fx'] = ''
        for i in range(len(data)):
            if re.findall('本地推',data.at[i,'产品线']) and data.at[i,'预结算标签'] != '收量':
                data.at[i,'product_name_fx'] = str(data.at[i,'行业类别']) + '-' + str(data.at[i,'预结算标签'])
            elif re.findall('广告',data.at[i,'产品线']) and data.at[i,'预结算标签'] != '收量':
                data.at[i,'product_name_fx'] = data.at[i,'行业类别']
            elif re.findall('千川',data.at[i,'产品线']) and data.at[i,'预结算标签'] != '收量':
                data.at[i,'product_name_fx'] = 'TT-千川-激励期'
                data.at[i,'new_monthly_consumption'] = data.at[i,'千川激励周期内消耗']
            elif re.findall('品牌', data.at[i, '产品线']) and data.at[i,'预结算标签'] != '收量':
                data.at[i, 'product_name_fx'] = 'TT-品牌-非车-' + str(data.at[i,'新老户'])
            else:
                data.at[i,'product_name_fx'] = ''
            # 判断核算业绩消耗的客户是否需要加上上月的消耗
            if data.at[i,'新老户'] == '首次核算新单':
                c = data.at[i,'公司名称']
                if data.at[i,'count']>1: #判断是否为多个账户
                    m = data[data['公司名称'] == c]['上线180内在本月消耗'].idxmax()
                    if i == m:
                        data.at[i,'new_monthly_consumption'] = data.at[i,'上线180内在本月消耗'] + data.at[i,'账户上线截止上月底消耗']
        mg = self.margin_conversion()
        data['id'] = data['公司名称'].map(lambda x:chinaToLetter().modeKey(x)) + data['account_id'].map(lambda x:x if x not in ['NULL',np.nan] else '_').astype(str) + data['产品线'].map(lambda x:chinaToLetter().modeKey(x)) + data['签单金额'].astype(str)
        data['ad_id'] = data['ad_date'].replace('-','') + data['id'] + '_' +data.index.astype(str)
        data['ad_type'] = data['产品线']
        data['is_loan'] = data['账期'].map(lambda x: 1 if x=='是' else 0)
        data['joint_no'] = data['双算人员.1'].map(lambda x:kaSearchConsumption().employNo(x))
        data['joint_manager_no'] = data['双算经理姓名'].map(lambda x:kaSearchConsumption().employNo(x))
        data = data.rename(columns=self.columns)
        data = pd.merge(data,mg,on='product_name_fx',how='left')
        # data.to_csv(r'../data/1.csv',encoding='utf-8-sig',index=False)
        return data
    def uploadData(self,data):
        for i in range(len(data)):
            tmp = data.iloc[i, :].dropna()
            cols = tmp.index.tolist()
            client_col = [c for c in self.base_client_cols if c in cols]
            client_adv_col = [c for c in self.client_adver_cols if c in cols]
            salary_col = [c for c in self.salary_detail_cols if c in cols]
            self.data_refresh.insertTbData('tb_client_base', client_col, tuple(tmp[client_col].values.tolist()),'id')
            # 过滤掉消耗为0的客户信息
            if ('monthly_consumption' in client_adv_col) and (tmp['monthly_consumption'] != 0):
                self.data_refresh.insertTbData('tb_client_adver_info', client_adv_col,tuple(tmp[client_adv_col].values.tolist()), 'ad_id')
            self.data_refresh.insertTbData('tb_salary_detail', salary_col, tuple(tmp[salary_col].values.tolist()),'ad_id')

    def go(self):
        print('starting time: ',datetime.datetime.now())
        data = self.readFile()
        data = self.collateData(data)
        self.uploadData(data)

if __name__ == '__main__':
    # print("="*150)
    # print('The base info loading...... \n')
    # baseInfoForm = baseInfoForm()# 员工基础信息更新
    # baseInfoForm.go()
    # print("="*150)
    #
    # print('The margin info loading...... \n')
    # mg = margins() # 利润表对应信息更新
    # mg.go()
    # print("="*150)

    print('The product info loading...... \n')
    prtc = productCommission() #导入产品提成信息
    prtc.go()

    # print("="*150)
    # print('The KA commission info loading...... \n')
    # ka = kaSearchConsumption() #KA大搜消耗提成
    # ka.go()
    #
    # print("="*150)
    # print('The XHS commission info loading...... \n')
    # xhs = xhsConsumption() #xhs消耗提成
    # xhs.go()

    # print('='*150)
    # print('The Contractor info loading......')
    # cont = contractor() # 服务商消耗提成
    # cont.go()
    #
    # print('='*150)
    # print('The TT consumption of data loading......')
    # tt = ttConsumption()
    # tt.go()
