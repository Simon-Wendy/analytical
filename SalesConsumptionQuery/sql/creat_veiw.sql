create view view_commission as 
select
	tsd.ad_date '核算提成月度',
	tcb.client_name '公司名称',
	tcb.account_name '账户名称',
	tcb.platform '产品',
	case
		when tcb.platform = '产品售卖' then tcb.product_name_fx
		else coalesce(tcai.ad_type, tcb.product )
	end '客户类型',
	tdbi.second_level_dept '部门',
	tjbi.emp_name '姓名',
	tcb.receipt_amount '收款金额',
	tcb.service_fee '服务费',
	tcai.monthly_consumption '当月消耗',
	tcai.new_monthly_consumption '新单消耗',
	tcai.non_new_monthly_consumption '非新单消耗',
	tsd.new_order_profit '新单利润',
	tsd.renewal_profit '续费利润',
	tsd.new_order_commission_rate '新单系数',
	tsd.new_order_commission '新单提成',
	tsd.renewal_commission_rate '续费系数',
	tsd.renewal_commission '续费提成',
	tsd.rebate '返点',
	tsd.kpi_score '绩效',
	tsd.quarterly_back_pay_new '季度新单差额提成',
	tsd.quarterly_back_pay_renewal '季度续费差额提成',
	tsd.remarks '备注',
	if(tsd.is_loan = 1, '是', '否') '账期'
from
	tb_salary_detail tsd
left join tb_client_adver_info tcai on
	tsd.ad_id = tcai.ad_id
left join tb_client_base tcb on
	tsd.id = tcb.id
left join tb_jober_base_info tjbi on
	tcb.emp_no = tjbi.emp_no
left join tb_department_base_info tdbi on
	tjbi.dept_seq = tdbi.dept_seq;