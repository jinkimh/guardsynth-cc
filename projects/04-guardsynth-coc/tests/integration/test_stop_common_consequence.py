"""Independent expected consequences and preservation of original unknown semantics."""
from pathlib import Path
import sys
import unittest

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'PROJECT_REGISTRY.json').exists())
sys.path.insert(0,str(ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import execute_speed_contracts as e
from guard_synth_eblc.speed_common_consequence import derive


class CommonConsequenceTest(unittest.TestCase):
    def test_common_exclusion_and_legacy_unknown_are_distinct(self):
        contract=e.contract_for('STOP_REQUIRED','fixture',['fixture:rule'])
        before=repr(contract.raw)
        result=derive(contract,'TRUE',True)
        self.assertEqual(result['excluded_by_all_supported_branches'],['START_OR_ACCELERATE'])
        self.assertEqual(result['legacy_unknown_excluded'],[])
        self.assertFalse(result['motion_inferred'])
        self.assertFalse(result['positive_permission_inferred'])
        self.assertEqual(before,repr(contract.raw))
        checks=e.check_queries(e.compile_core_model(e.parse_core_model(result['proof_core'])))
        self.assertEqual(checks['query_count'],27)
        self.assertEqual(checks['agreement'],1)

    def test_unknown_conflict_false_and_invalid_cannot_supply_exclusion(self):
        contract=e.contract_for('STOP_REQUIRED','fixture',['fixture:rule'])
        for truth,valid in [('UNKNOWN',True),('CONFLICT',True),('FALSE',True),('TRUE',False)]:
            with self.subTest(truth=truth,valid=valid):
                self.assertEqual(derive(contract,truth,valid)['excluded_by_all_supported_branches'],[])
        with self.assertRaises(ValueError):
            derive(e.contract_for('SPEED_REDUCTION_REQUIRED','fixture',['fixture:rule']),'TRUE',True)


if __name__=='__main__':unittest.main()
