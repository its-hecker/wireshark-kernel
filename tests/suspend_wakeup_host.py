"""Host regression tests of actual kernel function bodies with mocked primitives.

This checks control flow only; it cannot validate real IRQ/concurrency behavior.
Run: python3 tests/suspend_wakeup_host.py
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]


def function(path, signature):
    source = (root / path).read_text()
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


freeze = function('kernel/power/process.c', 'static int try_to_freeze_tasks(')
wakeup = function('drivers/base/power/wakeup.c', 'void pm_system_wakeup(')
stub = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdarg.h>
#include <errno.h>
typedef long ktime_t;
struct task_struct { int unused; } task;
struct task_struct *current = (void *)0;
static unsigned long jiffies;
static int tasks, loop_index, pending;
static unsigned int freeze_timeout_msecs = 20;
static int tasklist_lock;
#define USEC_PER_MSEC 1000
#define msecs_to_jiffies(x) (x)
#define time_after(a,b) ((a) > (b))
#define for_each_process_thread(g,p) for ((g)=&task,(p)=(g),loop_index=0; loop_index<tasks; loop_index++)
static void read_lock(int *lock) { (void)lock; }
static void read_unlock(int *lock) { (void)lock; }
static bool freeze_task(struct task_struct *p) { (void)p; return true; }
static bool freezer_should_skip(struct task_struct *p) { (void)p; return false; }
static bool freezing(struct task_struct *p) { (void)p; return true; }
static bool frozen(struct task_struct *p) { (void)p; return false; }
static void sched_show_task(struct task_struct *p) { (void)p; }
static void freeze_workqueues_begin(void) {}
static bool freeze_workqueues_busy(void) { return false; }
static void show_workqueue_state(void) {}
static bool pm_wakeup_pending(void) { return pending; }
static ktime_t ktime_get_boottime(void) { return jiffies; }
static ktime_t ktime_sub(ktime_t a, ktime_t b) { return a-b; }
static unsigned int ktime_to_ms(ktime_t t) { return t; }
static void usleep_range(int a, int b) { (void)a; (void)b; jiffies++; }
static void mock_log(const char *fmt, ...) { (void)fmt; }
#define pr_cont mock_log
#define pr_err mock_log
typedef struct { int value; } atomic_t;
static atomic_t pm_abort_suspend;
static int wake_calls;
static int atomic_inc_return(atomic_t *v) { return ++v->value; }
static inline void atomic_inc(atomic_t *v) { ++v->value; }
static void s2idle_wake(void) { wake_calls++; }
'''
main = r'''
int main(void) {
    tasks=0; pending=0;
    assert(try_to_freeze_tasks(true)==0);
    pending=1;
    assert(try_to_freeze_tasks(true)==-EBUSY);
    tasks=1;
    assert(try_to_freeze_tasks(true)==-EBUSY);
    pending=0; jiffies=0;
    assert(try_to_freeze_tasks(true)==-EBUSY);
    assert(jiffies>freeze_timeout_msecs);
    pm_system_wakeup(); pm_system_wakeup(); pm_system_wakeup();
    assert(pm_abort_suspend.value==3 && wake_calls==1);
    pm_abort_suspend.value=0;
    pm_system_wakeup();
    assert(pm_abort_suspend.value==1 && wake_calls==2);
    return 0;
}
'''
with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary)
    (path / 'regression.c').write_text(stub + freeze + wakeup + main)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    str(path / 'regression.c'), '-o', str(path / 'regression')], check=True)
    subprocess.run([str(path / 'regression')], check=True)
print('Suspend/freezer and repeated-wakeup host regression checks passed.')
