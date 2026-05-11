package worker

import (
	"context"
	"fmt"
)

// Job is a unit of work processed by a worker.
type Job struct {
	ID      int
	Payload []byte
}

// process handles a single job. Replace with real work.
func process(ctx context.Context, j Job) error {
	select {
	case <-ctx.Done():
		return fmt.Errorf("process job %d: %w", j.ID, ctx.Err())
	default:
	}
	// Real work would go here.
	return nil
}

// StartWorker spawns a goroutine that processes jobs from the jobs channel
// until either the channel is closed or ctx is cancelled. The context is the
// goroutine's termination path, preventing leaks when the caller wants to
// shut down before jobs is closed.
func StartWorker(ctx context.Context, jobs <-chan Job) {
	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			case j, ok := <-jobs:
				if !ok {
					return
				}
				if err := process(ctx, j); err != nil {
					// Log-and-continue: a single bad job must not kill the worker.
					// Replace with the project's structured logger.
					fmt.Printf("worker: process job %d: %v\n", j.ID, err)
				}
			}
		}
	}()
}
