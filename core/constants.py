# Status Colors
STATUS_COLORS = {
    'potential': '#409EFF',      # Blue (潜在)
    'active': '#67c23a',         # Green (执行中/成交)
    'completed': '#409eff',      # Blue (已完成)
    'expired': '#f56c6c',        # Red (已过期)
    'terminated': '#e6a23c',     # Orange (已终止/流失)
    'draft': '#909399',          # Grey (草稿)
    'follow_up': '#E6A23C',      # Orange (跟进)
    'lost': '#303133',           # Black/Dark Grey (流失)
}

# Customer Module Statuses
CUSTOMER_STATUS_COLORS = {
    '成交': '#F56C6C',   # Red (Special case in original code)
    '流失': '#303133',   # Dark
    '跟进': '#E6A23C',   # Orange
    '潜在': '#409EFF',   # Blue
}

# Contract Module Statuses
CONTRACT_STATUS_MAP = {
    'draft': ('草稿', '#909399'),
    'active': ('执行中', '#67c23a'),
    'completed': ('已完成', '#409eff'),
    'expired': ('已过期', '#f56c6c'),
    'terminated': ('已终止', '#e6a23c')
}

# Business Module Statuses (Proxy Accounting)
BUSINESS_STATUS_COLORS = {
    'active': '#67c23a',    # Green
    'pending': '#E6A23C',   # Orange
    'inactive': '#909399',  # Grey
    'suspended': '#f56c6c', # Red
    'service_active': '#67c23a',    # 服务中
    'service_stopped': '#909399',   # 已停止
    'service_pending': '#E6A23C',   # 待服务
}

# Finance Module Statuses
FINANCE_STATUS_COLORS = {
    'income': '#67c23a',     # Green (收入)
    'expense': '#f56c6c',    # Red (支出)
    'pending': '#E6A23C',    # Orange (待处理)
    'completed': '#409eff',  # Blue (已完成)
}

# Finance Module Tag Colors
FINANCE_TAG_COLORS = {
    'contract': {
        'success': ['已签订'],
        'danger': ['未签订']
    },
    'project': {
        'success': ['已完结', '已交接'],
        'warning': ['未完结', '未交接']
    },
    'invoice': {
        'success': ['已开票'],
        'danger': ['未开票']
    }
}
