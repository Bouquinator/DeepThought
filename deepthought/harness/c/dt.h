/*
** dt.h — DeepThought C test harness.
**
** Write tests with DT_TEST(group, name, "description") { ... } and the
** DT_EXPECT_* / DT_ASSERT_* macros. Link with dt_main.c and dt_alloc.c.
** Every test runs in its own forked process: crashes, timeouts and leaks are
** reported per test. Results are written as DTP (JSON lines) to the fd named
** by $DT_REPORT_FD, or as readable text on stderr when it is unset.
*/

#ifndef DT_H
# define DT_H

# include <stddef.h>
# include <stdlib.h>
# include <string.h>
# include <stdio.h>
# include <unistd.h>

# define DT_PROTOCOL 1

typedef void	(*t_dt_fn)(void);

typedef struct s_dt_test
{
	const char	*group;
	const char	*name;
	const char	*desc;
	const char	*file;
	int			line;
	t_dt_fn		fn;
}	t_dt_test;

typedef struct s_dt_capture
{
	char	*data;
	size_t	len;
}	t_dt_capture;

/* registration */
void	dt_register(t_dt_test test);

# define DT_TEST(group, name, desc) \
	static void dt_fn_##group##__##name(void); \
	__attribute__((constructor)) static void dt_reg_##group##__##name(void) \
	{ \
		dt_register((t_dt_test){#group, #name, desc, __FILE__, __LINE__, \
			dt_fn_##group##__##name}); \
	} \
	static void dt_fn_##group##__##name(void)

/* checks: return 1 when ok. `fatal` stops the test on failure. */
int		dt_check(int ok, int fatal, const char *expr, const char *expected,
			const char *actual, const char *file, int line);
int		dt_check_int(long long actual, long long expected, int fatal,
			const char *expr, const char *file, int line);
int		dt_check_uint(unsigned long long actual, unsigned long long expected,
			int fatal, const char *expr, const char *file, int line);
int		dt_check_ptr(const void *actual, const void *expected, int fatal,
			const char *expr, const char *file, int line);
int		dt_check_str(const char *actual, const char *expected, int fatal,
			const char *expr, const char *file, int line);
int		dt_check_mem(const void *actual, const void *expected, size_t n,
			int fatal, const char *expr, const char *file, int line);
int		dt_check_bytes(const void *actual, size_t alen, const void *expected,
			size_t elen, int fatal, const char *expr, const char *file,
			int line);
int		dt_check_sign(long long actual, long long expected, int fatal,
			const char *expr, const char *file, int line);
void	dt_note(const char *fmt, ...);
/* describe the input being tested: shown with every failure (and crash) that follows */
void	dt_input(const char *fmt, ...);
void	dt_skip(const char *reason);
void	dt_fail(const char *msg, const char *file, int line);

# define DT__CHK(f, ...) f(__VA_ARGS__, __FILE__, __LINE__)

# define DT_EXPECT(cond) \
	dt_check(!!(cond), 0, #cond, "true", "false", __FILE__, __LINE__)
# define DT_ASSERT(cond) \
	dt_check(!!(cond), 1, #cond, "true", "false", __FILE__, __LINE__)
# define DT_EXPECT_EQ_INT(a, e)  DT__CHK(dt_check_int, (a), (e), 0, #a)
# define DT_ASSERT_EQ_INT(a, e)  DT__CHK(dt_check_int, (a), (e), 1, #a)
# define DT_EXPECT_EQ_SIZE(a, e) DT__CHK(dt_check_uint, (a), (e), 0, #a)
# define DT_ASSERT_EQ_SIZE(a, e) DT__CHK(dt_check_uint, (a), (e), 1, #a)
# define DT_EXPECT_EQ_PTR(a, e)  DT__CHK(dt_check_ptr, (a), (e), 0, #a)
# define DT_ASSERT_EQ_PTR(a, e)  DT__CHK(dt_check_ptr, (a), (e), 1, #a)
# define DT_EXPECT_EQ_STR(a, e)  DT__CHK(dt_check_str, (a), (e), 0, #a)
# define DT_ASSERT_EQ_STR(a, e)  DT__CHK(dt_check_str, (a), (e), 1, #a)
# define DT_EXPECT_EQ_MEM(a, e, n) DT__CHK(dt_check_mem, (a), (e), (n), 0, #a)
# define DT_ASSERT_EQ_MEM(a, e, n) DT__CHK(dt_check_mem, (a), (e), (n), 1, #a)
/* same sign (<0, 0, >0): for strcmp-like functions */
# define DT_EXPECT_SAME_SIGN(a, e) DT__CHK(dt_check_sign, (a), (e), 0, #a)
# define DT_EXPECT_NULL(a) \
	dt_check((a) == NULL, 0, #a " == NULL", "NULL", "non-NULL pointer", \
		__FILE__, __LINE__)
# define DT_ASSERT_NULL(a) \
	dt_check((a) == NULL, 1, #a " == NULL", "NULL", "non-NULL pointer", \
		__FILE__, __LINE__)
# define DT_EXPECT_NOT_NULL(a) \
	dt_check((a) != NULL, 0, #a " != NULL", "non-NULL pointer", "NULL", \
		__FILE__, __LINE__)
# define DT_ASSERT_NOT_NULL(a) \
	dt_check((a) != NULL, 1, #a " != NULL", "non-NULL pointer", "NULL", \
		__FILE__, __LINE__)
# define DT_FAIL(msg) dt_fail((msg), __FILE__, __LINE__)
/* allocated size of ptr (only checked when malloc hooks are active) */
# define DT_EXPECT_ALLOC_SIZE(ptr, n) \
	do { \
		if (dt_alloc_hooked()) \
			dt_check_uint(dt_alloc_size(ptr), (n), 0, \
				"allocated size of " #ptr, __FILE__, __LINE__); \
	} while (0)

/* output capture: everything written to `fd` while running `block` */
int		dt_capture_begin(int fd);
void	dt_capture_end(int fd, int token, t_dt_capture *out);
void	dt_capture_free(t_dt_capture *cap);

# define DT_CAPTURE_FD(fd, cap, block) \
	do { \
		int dt__tok = dt_capture_begin(fd); \
		block; \
		dt_capture_end(fd, dt__tok, &(cap)); \
	} while (0)
# define DT_CAPTURE_STDOUT(cap, block) DT_CAPTURE_FD(1, cap, block)

/*
** Compare an ft_ call against its reference: same stdout bytes, same return
** value. Typical use: DT_COMPARE_OUTPUT(ft_printf("%d", 42), printf("%d", 42));
*/
# define DT_COMPARE_OUTPUT(ft_call, ref_call) \
	do { \
		t_dt_capture dt__a; \
		t_dt_capture dt__b; \
		long long dt__ra = 0; \
		long long dt__rb = 0; \
		DT_CAPTURE_STDOUT(dt__a, dt__ra = (ft_call)); \
		DT_CAPTURE_STDOUT(dt__b, dt__rb = (ref_call)); \
		dt_check_bytes(dt__a.data, dt__a.len, dt__b.data, dt__b.len, 0, \
			"output of " #ft_call, __FILE__, __LINE__); \
		dt_check_int(dt__ra, dt__rb, 0, "return value of " #ft_call, \
			__FILE__, __LINE__); \
		dt_capture_free(&dt__a); \
		dt_capture_free(&dt__b); \
	} while (0)

/* fixtures: absolute path of a file in the suite's fixtures/ directory */
const char	*dt_fixture(const char *relpath);

/* allocation tracking (dt_alloc.c) */
void	dt_malloc_fail_at(int nth);
void	dt_malloc_fail_all(void);
void	dt_malloc_reset(void);
int		dt_malloc_calls(void);
void	dt_leaks_ignore(void);
size_t	dt_alloc_size(const void *ptr);

/* internal: used by dt_main.c */
void	dt_alloc_start(void);
void	dt_alloc_stop(void);
int		dt_alloc_leaks(size_t *bytes, size_t *count);
int		dt_alloc_hooked(void);
void	*dt_raw_malloc(size_t size);
void	dt_raw_free(void *ptr);

#endif
