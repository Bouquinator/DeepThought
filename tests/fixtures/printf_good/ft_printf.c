#include "ft_printf.h"

typedef struct s_spec
{
	int	minus;
	int	zero;
	int	hash;
	int	space;
	int	plus;
	int	width;
	int	prec;
}	t_spec;

static int	put(const char *s, int n)
{
	return ((int)write(1, s, n));
}

static int	pad(char c, int n)
{
	int	r = 0;

	while (n-- > 0)
		r += put(&c, 1);
	return (r);
}

static int	slen(const char *s)
{
	int	n = 0;

	while (s[n])
		n++;
	return (n);
}

static int	emit(t_spec *sp, const char *pre, const char *body, int blen, int zeros)
{
	int	plen = slen(pre);
	int	total = plen + zeros + blen;
	int	r = 0;
	int	zpad = sp->zero && !sp->minus && sp->prec < 0;

	if (!sp->minus && !zpad)
		r += pad(' ', sp->width - total);
	r += put(pre, plen);
	if (zpad)
		r += pad('0', sp->width - total);
	r += pad('0', zeros);
	r += put(body, blen);
	if (sp->minus)
		r += pad(' ', sp->width - total);
	return (r);
}

static int	number(t_spec *sp, unsigned long long v, int neg, const char *base, const char *prefix)
{
	char	buf[32];
	int		i = 32;
	int		b = slen(base);
	int		len;
	int		zeros;
	char	pre[4] = {0};

	while (v || i == 32)
	{
		buf[--i] = base[v % b];
		v /= b;
	}
	len = 32 - i;
	if (sp->prec == 0 && len == 1 && buf[31] == '0' && !(prefix && prefix[0] == 'p'))
		len = 0;
	if (neg)
		pre[0] = '-';
	else if (sp->plus)
		pre[0] = '+';
	else if (sp->space)
		pre[0] = ' ';
	if (prefix && prefix[0] == 'p')
		pre[0] = '0', pre[1] = 'x';
	else if (prefix && len && !(len == 1 && buf[31] == '0'))
		pre[0] = prefix[0], pre[1] = prefix[1];
	zeros = sp->prec > len ? sp->prec - len : 0;
	return (emit(sp, pre, buf + 32 - len, len, zeros));
}

static int	conv(char c, t_spec *sp, va_list *ap)
{
	char	ch;
	char	*s;
	long	n;
	int		len;
	void	*p;

	if (c == 'c' || c == '%')
	{
		ch = c == '%' ? '%' : (char)va_arg(*ap, int);
		sp->prec = -1;
		return (emit(sp, "", &ch, 1, 0));
	}
	if (c == 's')
	{
		s = va_arg(*ap, char *);
		if (!s)
			s = (sp->prec >= 0 && sp->prec < 6) ? "" : "(null)";
		len = slen(s);
		if (sp->prec >= 0 && sp->prec < len)
			len = sp->prec;
		sp->zero = 0;
		sp->prec = -1;
		return (emit(sp, "", s, len, 0));
	}
	if (c == 'p')
	{
		p = va_arg(*ap, void *);
		sp->plus = 0;
		sp->space = 0;
#ifdef __linux__
		if (!p)
			return (sp->prec = -1, emit(sp, "", "(nil)", 5, 0));
#endif
		return (number(sp, (unsigned long long)(unsigned long)p, 0, "0123456789abcdef", "p"));
	}
	if (c == 'd' || c == 'i')
	{
		n = va_arg(*ap, int);
		return (number(sp, n < 0 ? -n : n, n < 0, "0123456789", NULL));
	}
	sp->plus = 0;
	sp->space = 0;
	if (c == 'u')
		return (number(sp, va_arg(*ap, unsigned int), 0, "0123456789", NULL));
	if (c == 'x')
		return (number(sp, va_arg(*ap, unsigned int), 0, "0123456789abcdef", sp->hash ? "0x" : NULL));
	if (c == 'X')
		return (number(sp, va_arg(*ap, unsigned int), 0, "0123456789ABCDEF", sp->hash ? "0X" : NULL));
	return (put(&c, 1) + 0);
}

static const char	*parse(const char *f, t_spec *sp)
{
	*sp = (t_spec){0, 0, 0, 0, 0, 0, -1};
	while (*f == '-' || *f == '0' || *f == '#' || *f == ' ' || *f == '+')
	{
		sp->minus |= *f == '-';
		sp->zero |= *f == '0';
		sp->hash |= *f == '#';
		sp->space |= *f == ' ';
		sp->plus |= *f == '+';
		f++;
	}
	while (*f >= '0' && *f <= '9')
		sp->width = sp->width * 10 + *f++ - '0';
	if (*f == '.')
	{
		sp->prec = 0;
		f++;
		while (*f >= '0' && *f <= '9')
			sp->prec = sp->prec * 10 + *f++ - '0';
	}
	return (f);
}

int	ft_printf(const char *fmt, ...)
{
	va_list	ap;
	t_spec	sp;
	int		r = 0;

	va_start(ap, fmt);
	while (*fmt)
	{
		if (*fmt == '%' && fmt[1])
		{
			fmt = parse(fmt + 1, &sp);
			r += conv(*fmt, &sp, &ap);
		}
		else
			r += put(fmt, 1);
		fmt++;
	}
	va_end(ap);
	return (r);
}
