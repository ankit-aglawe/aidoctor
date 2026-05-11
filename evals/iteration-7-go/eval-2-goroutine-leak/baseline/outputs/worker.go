package worker

func StartWorker(jobs <-chan Job) {
	go func() {
		for j := range jobs {
			process(j)
		}
	}()
}
