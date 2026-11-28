// Touch ID check for `harness approve` and `harness merge-ok`. Exit 0 only when the person passed.
// Biometrics first; if they are not available, the device password.
import Foundation
import LocalAuthentication

let reason = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "Approve a harness change"
let ctx = LAContext()
var err: NSError?
let policy: LAPolicy = ctx.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &err)
    ? .deviceOwnerAuthenticationWithBiometrics
    : .deviceOwnerAuthentication

let done = DispatchSemaphore(value: 0)
var ok = false
ctx.evaluatePolicy(policy, localizedReason: reason) { success, _ in
    ok = success
    done.signal()
}
done.wait()
exit(ok ? 0 : 1)
