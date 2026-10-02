# model/classifier.py — 短线/长线分类

class Classifier:
    """基于因子权重的短线/长线分类器"""

    def __init__(self, config):
        self.short_factors = config["factor_categories"]["short_term"]
        self.long_factors = config["factor_categories"]["long_term"]
        self.short_thresh = config["scoring"]["short_term_threshold"]
        self.long_thresh = config["scoring"]["long_term_threshold"]

    def classify(self, factor_df, causal_factors):
        """
        输入：因子截面 + 有效因果因子
        输出：每只股票的 direction 标签
        """
        # 计算短线 / 长线因子的综合 MCI
        short_mci = sum(mci for n, mci in causal_factors if n in self.short_factors)
        long_mci = sum(mci for n, mci in causal_factors if n in self.long_factors)
        total = short_mci + long_mci

        if total == 0:
            return "观望"

        short_ratio = short_mci / total

        if short_ratio > self.short_thresh:
            return "短线"
        elif short_ratio < self.long_thresh:
            return "长线"
        return "混合"
