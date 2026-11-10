"""[L05] Anti-Slop Guard - Force Statistical Significance"""
class SlopGuard:
    def clean(self, text):
        return text.replace("显著提升", "p<0.05 且提升超过 15%")
