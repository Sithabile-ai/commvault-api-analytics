# Aging Policy Analysis Summary

**Generated:** 2025-11-14
**Database:** Commvault API Data Collection
**Total Plans Analyzed:** 278 Plans
**Total Retention Rules:** 518 Rules

---

## Executive Summary

This report provides a comprehensive analysis of aging (retention) policies configured across all Commvault Plans in the system. The analysis focuses on retention days, cycles, and aging enablement status.

### Key Findings

- ✅ **All retention rules have aging ENABLED** (518/518 = 100%)
- 📊 **Most common retention periods:**
  - 14 days: **141 rules** (27.2%)
  - 10 days: **91 rules** (17.6%)
  - 30 days: **76 rules** (14.7%)
  - 365 days (1 year): **74 rules** (14.3%)

---

## Critical Statistics

### Retention Period Counts

| Retention Days | Number of Rules | Percentage | Description |
|---------------:|----------------:|-----------:|:------------|
| **14 days** | **141** | **27.2%** | Most common short-term retention |
| **10 days** | **91** | **17.6%** | Second most common |
| **30 days** | **76** | **14.7%** | Standard monthly retention |
| **365 days** | **74** | **14.3%** | Annual retention |
| 730 days (2 years) | 16 | 3.1% | Long-term retention |
| 1825 days (5 years) | 8 | 1.5% | Compliance/legal retention |

### 30-Day and 14-Day Retention Breakdown

#### 📦 30-Day Retention Policies
- **Total storage copies with 30-day retention:** 76
- **Unique plans with 30-day retention:** 64

**Key Plans with 30-day retention:**
1. ALS_AD - 1 copy
2. ALS_FS - 2 copies (Primary + Cloud)
3. ALS_SQL - 1 copy
4. ALS_VM - 2 copies (Primary + Cloud)
5. ASEM Backup Plan - 2 copies
6. ActiveScale_EXT_Plan - 2 copies
7. AllBro_Backup Plan - 1 copy
8. CT Onsite Backup - 2 copies
9. Cani Rusk Plan - 1 copy
10. Capri Linux Server Plan - 1 copy
11. Capri Linux Test - 1 copy
12. Capri Server Plan - 1 copy
13. CapriChem Backup Plan - 1 copy
14. ClockWorks SQL Plan - 1 copy
15. ClockWorks_FS_Plan - 1 copy
16. Daikin Backup Plan - 2 copies
17. Dickon Hall Foods Backup Plan - 1 copy
18. Edward Backup Plan - 1 copy
19. Extraordinary Backup Plan - 1 copy
20. Fasken Backup Plan - 1 copy
21. Finlar CPT Backup Plan - 1 copy
22. Formax Endpoint Plan - 1 copy
23. Formax_AD - 1 copy
24. Formax_FS - 1 copy
25. Formax_SQL - 1 copy
26. Formax_VM - 1 copy
27. GVSupreme Backup Plan - 2 copies
28. Gordon Verhoef & Krause Backup Plan - 1 copy
29. LawExplorer Backup Plan - 1 copy
30. MIFA Server Plan - 1 copy
31. MIFA_File_Plan - 1 copy
32. MKLM_Plan - 1 copy
33. MMH - Christie House - 1 copy
34. MMH - MOZ - 1 copy
35. MMH-BOT - 1 copy
36. MMH-GHA - 1 copy
37. MMH-Kingsway - 1 copy
38. MMH-NAM - 1 copy
39. MediKredit - Treaco Plan - 2 copies
40. MediKredit_DR Center - 1 copy
41. MediKredit_HeadOffice - 1 copy
42. Medikredit - BI SQL backup - 1 copy
43. Mentor-Plan - 1 copy
44. Mentor-Server-Plan - 2 copies
45. Plumblink_Laptop_Plan - 2 copies
46. Profica - 1 copy
47. QASTEST - 1 copy
48. Rialto Foods Backup Plan - 2 copies
49. Sasfin Backup Plan - 1 copy
50. Server Plan Friday Full - 1 copy
51. Server Plan Saturday Full - 1 copy
52. Silicone Server Plan - 1 copy
53. Sithabile Staff - 1 copy
54. SMD Server Plan - 1 copy
55. Southern Sun OR Tambo Plan - 1 copy
56. SouthernSun Local Plan - 1 copy
57. STS_Exchange - 1 copy
58. Syntech Backup Plan - 1 copy
59. Syntech Server Plan - 1 copy
60. Top Vending Hyper-V - 1 copy
61. Traficc Backup Plan - 1 copy
62. UmAfrika Backup Server - 1 copy
63. Universal Nas Plan - 1 copy
64. Van Der Vyver Linux Plan - 2 copies

#### 📦 14-Day Retention Policies
- **Total storage copies with 14-day retention:** 141
- **Unique plans with 14-day retention:** 131

**Key Plans with 14-day retention:**
1. A.R.B Electrical Backup Plan - Cloud copy
2. ALS_AD - Cloud copy
3. ALS_SQL - Cloud copy
4. AMT Server Plan - Cloud copy
5. AS2 Server Foundation Plan - Cloud copy
6. Allan Gray Backup Plan - Cloud copy
7. Apex Backup Plan - Cloud copy
8. Apex Plan - 2 copies
9. BallStraathof_AD - Cloud copy
10. BallStraathof_FS - Cloud copy
11. BallStraathof_Oracle - Cloud copy
12. BallStraathof_SQL - Cloud copy
13. BallStraathof_VM - Cloud copy
14. Blue Turtle Plan V1 - Cloud copy
15. Blue Turtle Plan v2 - Cloud copy
16. CCIC AD Plan - Cloud copy
17. CCIC FS Plan - Cloud copy
18. CCIC SQL Plan - Cloud copy
19. CCIC VM Plan - Cloud copy
20. Capri Server Plan - Cloud copy
21. CapriChem Backup Plan - Cloud copy
22. Chartered Wealth Solutions Plan - 2 copies
23. ClifftopLodge Backup Plan - 2 copies
24. DLM Backup Plan - Cloud copy
25. Dickon Hall Foods Backup Plan - Cloud copy
26. ESA Plan - Cloud copy
27. Empact Group V1 - Cloud copy
28. Empact Group V2 - Cloud copy
29. Energy Partners Backup Plan - Cloud copy
30. Extraordinary Backup Plan - Cloud copy
31. Filmfinity Backup Plan - Cloud copy
32. Filmfinity SQL Backup Plan - Cloud copy
33. Finbond Mutual Bank Backup Plan - Cloud copy
34. Finlar CPT Backup Plan - Cloud copy
35. Finlar JHB Backup Plan - Cloud copy
36. Formax_FS - Cloud copy
37. Formax_VM - Cloud copy
38. Front Runner SQL Plan - 2 copies
39. Front Runner Server Plan - Cloud copy
40. Henley Server Plan - Cloud copy
41. IBI Every2Hours - Cloud copy
42. IBI Everyday Full - Cloud copy
43. IBI Server Backup - Cloud copy

... and many more (131 unique plans total)

---

## Retention Distribution Analysis

### Short-Term Retention (< 30 days)
- 1 day: 1 rule
- 3 days: 1 rule
- 4 days: 1 rule
- 5 days: 3 rules
- 7 days: 17 rules
- **10 days: 91 rules** ⭐ Very common
- **14 days: 141 rules** ⭐ Most common
- 15 days: 22 rules
- 21 days: 4 rules
- 29 days: 2 rules

**Total Short-Term:** 283 rules (54.6%)

### Medium-Term Retention (30-90 days)
- **30 days: 76 rules** ⭐ Common
- 31 days: 1 rule
- 60 days: 1 rule
- 90 days: 3 rules
- 91 days: 1 rule
- 93 days: 18 rules

**Total Medium-Term:** 100 rules (19.3%)

### Long-Term Retention (> 90 days)
- 182 days (6 months): 5 rules
- 183 days: 2 rules
- 186 days: 4 rules
- 364 days: 4 rules
- **365 days (1 year): 74 rules** ⭐ Very common
- 730 days (2 years): 16 rules
- 1095 days (3 years): 1 rule
- 1825 days (5 years): 8 rules
- 1826 days: 1 rule
- 2555 days (7 years): 1 rule

**Total Long-Term:** 116 rules (22.4%)

### Infinite Retention
- Plans with infinite retention detected
- Typically used for cloud/archive copies
- Special retention for Office 365, SharePoint, OneDrive, Teams

---

## Aging Status

### Overall Aging Enablement
- ✅ **Aging ENABLED:** 518 rules (100%)
- ❌ **Aging DISABLED:** 0 rules (0%)

**Conclusion:** All retention policies have data aging enabled, meaning Commvault will automatically prune data according to the configured retention periods.

---

## Pattern Analysis

### Common Retention Strategy
Most organizations follow a **tiered retention strategy**:

1. **Primary Copy:** 10-30 days (fast recovery)
   - 10 days: Quick operational recovery
   - 14 days: 2-week operational window
   - 30 days: Monthly backup retention

2. **Cloud/Secondary Copy:** 14-365 days (disaster recovery)
   - 14 days: Short-term cloud backup
   - 30 days: Monthly cloud retention
   - 365 days: Annual compliance retention

3. **Archive Copy:** 365-1825+ days (long-term compliance)
   - 1 year: Standard compliance
   - 2 years: Financial records
   - 5+ years: Legal/regulatory compliance

### Cloud Copy Retention
Most cloud copies have **14-day retention**, which is shorter than primary copies. This suggests:
- Cloud storage is used for disaster recovery, not long-term retention
- Cost optimization strategy (shorter retention = lower cloud storage costs)
- Primary storage kept on-premises for faster recovery

---

## Recommendations

### Current State Assessment
✅ **Strengths:**
- All policies have aging enabled (no orphaned data)
- Well-distributed retention periods
- Clear tiered strategy (primary vs cloud)
- Compliance-focused long-term retention

⚠️ **Areas for Review:**
1. **Very short retention (1-5 days):** Only 8 rules
   - Verify these are intentional (test environments?)
   - Example: "Irene Test" has 1-day retention

2. **Inconsistent retention across similar plans:**
   - Some plans have 10 days, others have 14 days
   - Consider standardizing to 10, 14, or 30-day tiers

3. **Cloud copy strategy:**
   - Most cloud copies have 14-day retention
   - Consider if this meets disaster recovery requirements

### Optimization Opportunities

1. **Standardize Retention Tiers:**
   - Tier 1: 14 days (operational recovery)
   - Tier 2: 30 days (monthly backups)
   - Tier 3: 365 days (annual compliance)
   - Tier 4: 1825+ days (legal/regulatory)

2. **Review Short Retention Plans:**
   - Speedspace: 4 days
   - Simera NAS: 3 days
   - Irene Test: 1 day

3. **Cost Optimization:**
   - Cloud copies with 14-day retention: Review if adequate
   - Consider extending critical systems to 30 days
   - Archive old data to cheaper storage tiers

---

## Detailed Statistics Tables

### Top 20 Plans by Average Retention

| Plan Name | Copies | Min Days | Max Days | Avg Days | Aging Enabled |
|:----------|-------:|---------:|---------:|---------:|--------------:|
| Energy Partners Archive Plan | 1 | 2555 | 2555 | 2555.0 | 1/1 |
| Amaro Foods Backup Plan | 2 | 93 | 1826 | 959.5 | 2/2 |
| MIFA Plan | 2 | 365 | 1825 | 912.5 | 2/2 |
| MIFA_File_Plan | 2 | 30 | 1825 | 912.5 | 2/2 |
| MIFA Server Plan | 2 | 30 | 1825 | 912.5 | 2/2 |
| Bronze Endpoint | 2 | 365 | 730 | 547.5 | 2/2 |
| Accelerate Property Laptop Plan | 2 | 365 | 730 | 547.5 | 2/2 |
| Medikredit - BI SQL backup | 2 | 30 | 1095 | 547.5 | 2/2 |
| AllBro_Backup Plan | 2 | 30 | 364 | 197.0 | 2/2 |
| Blue Turtle Plan V1 | 2 | 14 | 364 | 189.0 | 2/2 |
| Blue Turtle Plan v2 | 2 | 14 | 364 | 189.0 | 2/2 |
| A.R.B Electrical Backup Plan | 2 | 14 | 365 | 189.5 | 2/2 |

### Plans with Shortest Retention

| Plan Name | Copies | Retention Days | Purpose |
|:----------|-------:|---------------:|:--------|
| Irene Test | 1 | 1 | Test environment |
| Simera NAS Backup Plan | 1 | 3 | Short-term NAS backup |
| Speedspace Backup Plan | 2 | 4 | Short operational window |
| Southern Sun Plans | 3 | 5 | Short hotel backup |

---

## Report Files Generated

1. **aging_policy_report.txt** - Full detailed report with all plans listed
2. **AGING_POLICY_SUMMARY.md** - This executive summary document

---

## Next Steps

1. ✅ Review plans with very short retention (< 7 days)
2. ✅ Standardize retention tiers across organization
3. ✅ Verify cloud retention meets DR requirements
4. ✅ Document retention policy rationale
5. ✅ Schedule regular retention policy audits

---

**Report Generated By:** Commvault API Data Collection Tool
**Analysis Script:** analyze_aging_policies.py
**Database:** Database/commvault.db
