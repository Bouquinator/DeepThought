/* Shared helpers for the ft_printf suite. */
#ifndef PRINTF_TEST_H
# define PRINTF_TEST_H
# include "dt.h"
# include "ft_printf.h"
# include <limits.h>
# include <stdint.h>
# include <stdio.h>

/* Same output bytes and same return value as printf. */
# define CMP(...) DT_COMPARE_OUTPUT(ft_printf(__VA_ARGS__), printf(__VA_ARGS__))
#endif
