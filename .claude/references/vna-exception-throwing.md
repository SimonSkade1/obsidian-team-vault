# Throwing a VNA exception

An exception interrupts the run: the controller has to work out what to do, a fresh agent usually starts your item over, and sometimes everything waits for the user. So the bar is high.

## Before you throw

1. Look for the answer in the purpose and spec of the parent project, and of its parent.
2. Where a sensible guess exists, proceed on it.
3. Throw when going on would probably be wasted or harmful. The usual cases:
	1. The item's instructions contradict each other or make no sense.
	2. A decision or fact is missing that the work hangs on, and no guess is safe.
	3. The item is too big for one run.
	4. The spec contradicts what you find.
	5. You tried and could not do the work.
	6. The work needs a step only a human can take, such as logging in or paying.

## How

Write `# Exception` into the file you were run on, above every other heading. For a spec or plan agent that file is its own task, not the project. The controller, and sometimes the user, decide from this section alone, so write it for a reader without your context:

```
# Exception

**What is wrong:**

**What was tried, and the state of partial work:**

**What would unblock it:** <as questions in the checkpoint question format, where there are any>
```

Set the file's `status` to `on-hold` and end your run. Change no other property: whether the user is needed is the controller's call.
