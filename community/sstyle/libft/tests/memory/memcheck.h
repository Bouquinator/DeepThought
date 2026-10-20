/*
** Memory cases (from the CodeTester's "memory" suite): for a function that
** allocates,
**   1. a normal call leaves nothing allocated once its result is freed;
**   2. when its Nth malloc fails (for every N the call makes), it returns
**      NULL and frees everything it had already allocated.
** Uses DeepThought's allocation hooks: works on macOS and Linux.
*/
#ifndef MEMCHECK_H
# define MEMCHECK_H
# include "../sstyle.h"

static inline void	release_plain(void *result)
{
	free(result);
}

static inline void	release_split(void *result)
{
	char	**arr;
	int		i;

	arr = (char **)result;
	if (!arr)
		return ;
	i = 0;
	while (arr[i])
		free(arr[i++]);
	free(arr);
}

static inline void	check_case(const char *name, void *(*call)(void),
	void (*release)(void *))
{
	char	label[128];
	size_t	before;
	void	*result;
	int		allocs;
	int		n;

	/* 1. normal call: result freed by us → nothing may remain */
	before = dt_alloc_live();
	dt_malloc_reset();
	result = call();
	allocs = dt_malloc_calls();
	release(result);
	snprintf(label, sizeof(label), "%s: leaked blocks after free(result)", name);
	DT_CHECK_INT(label, (int)(dt_alloc_live() - before), 0);
	/* 2. make each of its allocations fail in turn */
	n = 1;
	while (n <= allocs)
	{
		dt_input("%s while malloc #%d of %d fails", name, n, allocs);
		before = dt_alloc_live();
		dt_malloc_fail_at(n);
		result = call();
		dt_malloc_reset();
		snprintf(label, sizeof(label), "%s: malloc #%d of %d fails → NULL", name, n, allocs);
		DT_CHECK_PTR(label, result, NULL);
		release(result);
		snprintf(label, sizeof(label), "%s: malloc #%d of %d fails → leaked blocks", name, n, allocs);
		DT_CHECK_INT(label, (int)(dt_alloc_live() - before), 0);
		n++;
	}
	dt_leaks_ignore();	/* reported step by step above */
}
#endif
