#include "sstyle.h"
/*
** NOTE: Your ft_memchr.c defines the function as 'memchr' instead of
** 'ft_memchr'. Rename it to 'ft_memchr' and update libft.h accordingly.
** Until fixed, this test file will fail to link (undefined reference).
*/

static void	*ref_memchr(const void *s, int c, size_t n)
{
	const unsigned char	*p;

	p = (const unsigned char *)s;
	while (n--)
	{
		if (*p == (unsigned char)c)
			return ((void *)p);
		p++;
	}
	return (NULL);
}

static void	t_memchr(const char *label,
	const void *s, int c, size_t n)
{
	void		*ref;
	void		*got;
	ptrdiff_t	roff;
	ptrdiff_t	goff;

	ref = ref_memchr(s, c, n);
	got = ft_memchr(s, c, n);
	if (ref == NULL && got == NULL)
	{
	}
	else if (ref == NULL || got == NULL)
	{
		DT_FAILF("%s: expected %s, got %s", label, ref ? "ptr" : "NULL", got ? "ptr" : "NULL");
	}
	else
	{
		roff = (const unsigned char *)ref - (const unsigned char *)s;
		goff = (const unsigned char *)got - (const unsigned char *)s;
		if (!(roff == goff))
		{
			DT_FAILF("%s: expected offset %ld, got %ld", label, (long)roff, (long)goff);
		}
	}
}

DT_TEST(ft_memchr, find_first_l_at_offset_2, "find first 'l' at offset 2")
{
	const char		*s = "Hello, World!";

	/* repeated char: first occurrence returned */
	t_memchr("find first 'l' at offset 2", s, 'l', 13);
}

DT_TEST(ft_memchr, find_h_at_offset_0, "find 'H' at offset 0")
{
	const char		*s = "Hello, World!";

	/* repeated char: first occurrence returned */
	t_memchr("find 'H' at offset 0", s, 'H', 13);
}

DT_TEST(ft_memchr, find_char_at_exactly_position_n, "find char at exactly position n-1 (last examined byte)")
{
	t_memchr("find char at pos n-1", "abcde", 'e', 5);
}

DT_TEST(ft_memchr, char_just_past_n_not_found, "char just past n not found")
{
	/* search range shorter than string: char at pos n is not found */
	t_memchr("char just past n not found", "abcde", 'e', 4);
}

DT_TEST(ft_memchr, n_0_to_null, "n=0 → NULL")
{
	const char		*s = "Hello, World!";

	/* search range shorter than string: char at pos n is not found */
	t_memchr("n=0 → NULL", s, 'H', 0);
}

DT_TEST(ft_memchr, binary, "binary: 0x00 at offset 0")
{
	unsigned char	bin[] = {0x00, 0x01, 0xFF, 0x42};

	/* search range shorter than string: char at pos n is not found */
	t_memchr("binary: 0x00 at offset 0", bin, 0x00, 4);
}

DT_TEST(ft_memchr, binary_2, "binary: 0xFF at offset 2")
{
	unsigned char	bin[] = {0x00, 0x01, 0xFF, 0x42};

	/* search range shorter than string: char at pos n is not found */
	t_memchr("binary: 0xFF at offset 2", bin, 0xFF, 4);
}

DT_TEST(ft_memchr, binary_3, "binary: not found")
{
	unsigned char	bin[] = {0x00, 0x01, 0xFF, 0x42};

	/* search range shorter than string: char at pos n is not found */
	t_memchr("binary: not found", bin, 0xAB, 4);
}

DT_TEST(ft_memchr, c_is_masked_to_unsigned_char, "c is masked to unsigned char: 'a' + 256 == 353, (uchar)353 == 'a'")
{
	t_memchr("c > 255 masked to 'a'", "abc", 'a' + 256, 3);
}
