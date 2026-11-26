"""
Contamination Profiling and Treatment Recommendation Engine (SIH26023).
Computes Water Quality Index (WQI), parameter risk profiling against EPA/CPCB standards,
generates multi-stage treatment trains, chemical dosing schedules, and reuse suitability matrices.
"""

# Standard Permissible Limits for Greywater Reuse (Based on CPCB, EPA Water Reuse Guidelines, and WHO)
PERMISSIBLE_LIMITS = {
    'pH': {'min': 6.5, 'max': 8.5, 'ideal': 7.0, 'weight': 4},
    'TDS': {'max': 500.0, 'ideal': 0.0, 'weight': 3},
    'BOD': {'max': 30.0, 'ideal': 0.0, 'weight': 5},
    'COD': {'max': 100.0, 'ideal': 0.0, 'weight': 4},
    'Turbidity': {'max': 5.0, 'ideal': 0.0, 'weight': 3},
    'EC': {'max': 800.0, 'ideal': 0.0, 'weight': 2},
    'TSS': {'max': 30.0, 'ideal': 0.0, 'weight': 4},
    'Oil_and_Grease': {'max': 5.0, 'ideal': 0.0, 'weight': 4},
    'Temperature': {'max': 35.0, 'ideal': 25.0, 'weight': 1}
}

class TreatmentRecommender:
    def __init__(self):
        # Calculate normalized relative weights for WQI
        total_w = sum(p['weight'] for p in PERMISSIBLE_LIMITS.values())
        self.weights = {k: p['weight'] / total_w for k, p in PERMISSIBLE_LIMITS.items()}

    def calculate_wqi(self, sample_dict):
        """
        Calculates Water Quality Index (WQI) using the Weighted Arithmetic Index Method:
        WQI = sum(W_i * q_i)
        where q_i = |V_i - V_ideal| / (S_i - V_ideal) * 100
        """
        sub_indices = {}
        total_score = 0.0

        for param, limits in PERMISSIBLE_LIMITS.items():
            if param not in sample_dict:
                continue

            val = float(sample_dict[param])
            ideal = limits['ideal']
            
            if param == 'pH':
                if val >= 7.0:
                    qi = ((val - 7.0) / (limits['max'] - 7.0)) * 100.0
                else:
                    qi = ((7.0 - val) / (7.0 - limits['min'])) * 100.0
            elif param == 'Temperature':
                qi = max(0.0, (val - ideal) / (limits['max'] - ideal) * 100.0)
            else:
                qi = (val / limits['max']) * 100.0

            sub_score = self.weights[param] * qi
            sub_indices[param] = round(float(qi), 2)
            total_score += sub_score

        wqi = round(float(total_score), 2)

        # Classification based on standard WQI scales
        if wqi <= 50:
            status = 'Excellent'
            color = '#00f0ff'
            category_hint = 'Low Contamination'
        elif wqi <= 100:
            status = 'Good / Moderate'
            color = '#00ff88'
            category_hint = 'Medium Contamination'
        elif wqi <= 200:
            status = 'Poor / High Contamination'
            color = '#ffb703'
            category_hint = 'High Contamination'
        else:
            status = 'Very Poor / Severe Contamination'
            color = '#ff0055'
            category_hint = 'Severe Contamination'

        return {
            'wqi': wqi,
            'status': status,
            'color': color,
            'category_hint': category_hint,
            'sub_indices': sub_indices
        }

    def generate_parameter_profile(self, sample_dict):
        """
        Profiles individual parameters against standards, flagging threshold breaches and excess ratios.
        """
        profile = []
        violations_count = 0

        for param, limits in PERMISSIBLE_LIMITS.items():
            if param not in sample_dict:
                continue
            val = float(sample_dict[param])
            max_limit = limits['max']
            min_limit = limits.get('min', 0.0)

            is_safe = True
            severity = 'Safe'
            excess_ratio = 1.0

            if param == 'pH':
                if val < min_limit or val > max_limit:
                    is_safe = False
                    severity = 'Critical' if (val < 5.5 or val > 9.5) else 'Moderate'
                    excess_ratio = round(abs(val - 7.0) / 1.5, 2)
                    violations_count += 1
            else:
                if val > max_limit:
                    is_safe = False
                    excess_ratio = round(val / max_limit, 2)
                    violations_count += 1
                    if excess_ratio > 3.0:
                        severity = 'Severe'
                    elif excess_ratio > 1.5:
                        severity = 'High'
                    else:
                        severity = 'Moderate'

            profile.append({
                'parameter': param,
                'value': val,
                'standard_limit': f"{min_limit}-{max_limit}" if param == 'pH' else f"< {max_limit}",
                'is_safe': is_safe,
                'severity': severity,
                'excess_ratio': excess_ratio
            })

        return {
            'violations_count': violations_count,
            'parameters': profile
        }

    def generate_treatment_recommendation(self, sample_dict, category=None):
        """
        Designs comprehensive multi-stage treatment train, chemical dosing schedules,
        and water reuse suitability ratings.
        """
        wqi_info = self.calculate_wqi(sample_dict)
        if category is None or category == 'Unknown':
            category = wqi_info['category_hint']

        ph = float(sample_dict.get('pH', 7.0))
        tds = float(sample_dict.get('TDS', 400.0))
        bod = float(sample_dict.get('BOD', 50.0))
        cod = float(sample_dict.get('COD', 120.0))
        turbidity = float(sample_dict.get('Turbidity', 20.0))
        tss = float(sample_dict.get('TSS', 50.0))
        oil_grease = float(sample_dict.get('Oil_and_Grease', 8.0))

        # --- Stage 1: Pre-treatment / Physical Separation ---
        stage1_units = ['Bar Screen & Lint Trap (Removes hair, fibers, coarse particles)']
        if oil_grease > 8.0:
            stage1_units.append(f'Automated Grease Trap / Oil Skimmer (Oil & Grease is {oil_grease} mg/L; reduces fat caps)')
        if oil_grease > 40.0:
            stage1_units.append('Dissolved Air Flotation (DAF) Unit for heavy lipid separation')
        stage1_units.append('Equalization Basin with diffused aeration (HRT: 4-6 hours to dampen load spikes)')

        # --- Stage 2: Chemical Coagulation & Flocculation ---
        pac_dose = round(12.0 + 0.22 * turbidity + 0.08 * tss, 1) # mg/L
        alum_alt_dose = round(pac_dose * 1.6, 1) # mg/L
        polymer_aid_dose = round(0.5 + 0.01 * tss, 2) # mg/L anionic polyacrylamide
        
        stage2_units = [
            f'Chemical Dosing Unit: Polyaluminum Chloride (PAC) @ {pac_dose} mg/L (or Alum @ {alum_alt_dose} mg/L)',
            f'Coagulant Aid: Anionic Polymer @ {polymer_aid_dose} mg/L for floc strengthening',
            'High-Efficiency Tube Settler / Lamella Clarifier (90-95% TSS & turbidity settling)'
        ]

        if ph < 6.5:
            stage2_units.append(f'pH Correction (Alkali): Sodium Hydroxide (NaOH) dosing to raise pH from {ph} to 7.2')
        elif ph > 8.5:
            stage2_units.append(f'pH Correction (Acid): Sulfuric Acid (H2SO4) dosing to neutralize pH from {ph} to 7.4')

        # --- Stage 3: Biological & Filtration Process ---
        stage3_units = []
        if category == 'Low Contamination':
            stage3_units = [
                'Pressure Dual-Media Sand & Anthracite Filter (Removes residual suspended micro-flocs)',
                'Constructed Subsurface Wetland Bed (Optional passive ecological polishing)'
            ]
        elif category == 'Medium Contamination':
            stage3_units = [
                'Moving Bed Biofilm Reactor (MBBR) with high surface area carriers (Removes BOD & biodegradable organics)',
                'Secondary Clarifier & Sludge Recirculation',
                'Dual-Media Sand/Carbon Filter'
            ]
        elif category == 'High Contamination':
            stage3_units = [
                'Submerged Aerobic Membrane Bioreactor (MBR) with 0.04 µm Ultrafiltration hollow fiber modules',
                'Continuous aeration with coarse bubble scouring to prevent membrane fouling',
                'Sludge Digestor & Dewatering Screw Press'
            ]
        else: # Severe Contamination
            stage3_units = [
                'High-Rate Upflow Anaerobic Sludge Blanket (UASB) Pre-digestion',
                'Submerged Aerobic Membrane Bioreactor (MBR) with auto backwash and chemical cleaning CIP',
                'Electrocoagulation Cell for non-biodegradable surfactants'
            ]

        # --- Stage 4: Tertiary / Advanced Oxidation & Adsorption ---
        stage4_units = [
            'Granular Activated Carbon (GAC) Adsorber (Removes color, odor, residual surfactants, and trace micro-pollutants)'
        ]
        if cod > 200.0 or category in ('High Contamination', 'Severe Contamination'):
            stage4_units.append('Advanced Oxidation Process (AOP): UV-C + Hydrogen Peroxide (H2O2 @ 25 mg/L) for recalcitrant COD breakdown')
        if tds > 900.0 or category == 'Severe Contamination':
            stage4_units.append(f'Reverse Osmosis (RO) Polishing System (TDS is {tds} mg/L; achieves desalination to < 200 mg/L)')

        # --- Stage 5: Disinfection & Storage ---
        uv_dose = '40 mJ/cm² (Medium-pressure UV reactor)'
        chlorine_dose = '2.5 mg/L Sodium Hypochlorite (maintains 0.5-1.0 mg/L residual in recycled distribution line)'
        stage5_units = [
            f'Primary Disinfection: In-line UV Disinfection System @ {uv_dose}',
            f'Secondary Residual Disinfection: Chlorination @ {chlorine_dose}',
            'Treated Water Storage Tank with level-controlled redistribution pump skid'
        ]

        # --- Reuse Suitability Matrix ---
        suitability = {
            'toilet_flushing': {
                'title': 'Toilet & Urinal Flushing',
                'suitable': True,
                'requirement': 'BOD < 10, Turbidity < 2, TSS < 10',
                'status': 'Fully Suitable with Stage 1-3 & Disinfection'
            },
            'landscape_irrigation': {
                'title': 'Landscape & Garden Irrigation',
                'suitable': True,
                'requirement': 'pH 6.5-8.5, TDS < 800, BOD < 20',
                'status': 'Suitable for Sub-surface & Drip Irrigation'
            },
            'vehicle_washing': {
                'title': 'Vehicle & Equipment Washing',
                'suitable': category in ('Low Contamination', 'Medium Contamination') or tds < 800,
                'requirement': 'TDS < 500, Turbidity < 5, Oil & Grease < 1',
                'status': 'Suitable after GAC Filtration' if tds < 800 else 'Requires RO Desalination'
            },
            'industrial_cooling': {
                'title': 'Cooling Tower Makeup Water',
                'suitable': tds < 1000 and oil_grease < 5,
                'requirement': 'TDS < 800, TSS < 10, Hardness controlled',
                'status': 'Suitable after Softening / RO' if tds > 600 else 'Suitable'
            },
            'construction_dust': {
                'title': 'Construction & Dust Suppression',
                'suitable': True,
                'requirement': 'BOD < 30, TSS < 50',
                'status': 'Directly Usable after Stage 2 Clarification'
            },
            'environmental_discharge': {
                'title': 'Surface Water / Drain Discharge',
                'suitable': True,
                'requirement': 'Complies with CPCB/EPA General Discharge Standards',
                'status': 'Complies with General Effluent Standards'
            }
        }

        return {
            'category': category,
            'wqi': wqi_info,
            'stages': {
                'stage1_pretreatment': {'title': 'Stage 1: Pre-treatment & Equalization', 'units': stage1_units},
                'stage2_coagulation': {'title': 'Stage 2: Chemical Coagulation & Clarification', 'units': stage2_units},
                'stage3_biological': {'title': 'Stage 3: Biological & Secondary Filtration', 'units': stage3_units},
                'stage4_tertiary': {'title': 'Stage 4: Tertiary Adsorption & Advanced Oxidation', 'units': stage4_units},
                'stage5_disinfection': {'title': 'Stage 5: Disinfection & Redistribution', 'units': stage5_units}
            },
            'chemical_dosing': {
                'pac_dose_mg_l': pac_dose,
                'alum_alt_dose_mg_l': alum_alt_dose,
                'polymer_dose_mg_l': polymer_aid_dose,
                'uv_dose': uv_dose,
                'chlorine_dose': chlorine_dose,
                'ph_adjustment_needed': ph < 6.5 or ph > 8.5
            },
            'suitability_matrix': suitability
        }
