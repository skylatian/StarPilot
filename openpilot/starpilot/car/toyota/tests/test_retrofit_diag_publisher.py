import unittest

from openpilot.cereal import messaging
from opendbc.car.toyota.tests.test_corolla_retrofit import CarBus, RETROFIT, STOCK
from opendbc.car.toyota.tests.test_retrofit_diag import stalk_0x69, stalk_diag, version_frame
from openpilot.starpilot.car.toyota.retrofit_diag_publisher import attach
from openpilot.starpilot.flm.fullrate_collector import MAX_WIRE_BYTES


def car_state_message(valid=True):
  return messaging.new_message('carState', valid=valid, logMonoTime=123_000_000)


class TestRetrofitDiagPublisher(unittest.TestCase):
  def test_other_platforms_unchanged(self):
    bus = CarBus(STOCK)
    bus.run(20)
    self.assertIsNone(attach(bus.CI.CS, None, car_state_message()))
    companion = messaging.new_message('starpilotCarState')
    companion.starpilotCarState.lateralAuthorityUnavailable = True
    self.assertIs(attach(bus.CI.CS, companion, car_state_message()), companion)
    self.assertFalse(companion.starpilotCarState._has('retrofitDiag'))

  def test_standalone_message_at_one_in_ten_frames(self):
    bus = CarBus(RETROFIT)
    sent = []
    for _ in range(100):
      bus.step([stalk_0x69(0, True), stalk_diag(boot=4, recoveries=1), version_frame(0x504, 0, "101526a")])
      message = attach(bus.CI.CS, None, car_state_message(valid=False))
      if message is not None:
        sent.append(message)
    self.assertEqual(len(sent), 10)
    diag = sent[-1].starpilotCarState.retrofitDiag
    self.assertFalse(sent[-1].valid)  # follows carState validity, still published
    self.assertEqual(sent[-1].logMonoTime, 123_000_000)
    self.assertEqual(sent[-1].starpilotCarState.sourceCarStateMonoTime, 123_000_000)
    self.assertTrue(diag.stalk.seen)
    self.assertEqual(diag.stalk.bootCount, 4)
    self.assertEqual(diag.stalk.firmwareVersion, "101526a")
    self.assertTrue(diag.stalkMainOn)
    self.assertEqual(diag.epsLkaState, 1)
    self.assertEqual(str(diag.lastRestartEcu), "none")
    self.assertLess(len(sent[-1].to_bytes()), MAX_WIRE_BYTES // 10)

  def test_existing_companion_carries_diagnostics_every_frame(self):
    bus = CarBus(RETROFIT)
    for _ in range(3):
      bus.step()
      companion = messaging.new_message('starpilotCarState', valid=True, logMonoTime=7)
      companion.starpilotCarState.lateralAuthorityUnavailable = True
      self.assertIs(attach(bus.CI.CS, companion, car_state_message()), companion)
      self.assertTrue(companion.starpilotCarState.lateralAuthorityUnavailable)
      self.assertTrue(companion.starpilotCarState._has('retrofitDiag'))


if __name__ == "__main__":
  unittest.main()
