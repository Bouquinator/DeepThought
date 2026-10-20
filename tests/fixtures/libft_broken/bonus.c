#include "libft.h"

t_list	*ft_lstnew(void *content)
{
	t_list *n = malloc(sizeof(t_list));
	if (!n) return (NULL);
	n->content = content; n->next = NULL;
	return (n);
}
void	ft_lstadd_front(t_list **lst, t_list *new) { if (!lst || !new) return ; new->next = *lst; *lst = new; }
int	ft_lstsize(t_list *lst) { int n = 0; while (lst) { n++; lst = lst->next; } return (n); }
t_list	*ft_lstlast(t_list *lst) { while (lst && lst->next) lst = lst->next; return (lst); }
void	ft_lstadd_back(t_list **lst, t_list *new)
{
	if (!lst || !new) return ;
	if (!*lst) *lst = new; else ft_lstlast(*lst)->next = new;
}
void	ft_lstdelone(t_list *lst, void (*del)(void *)) { if (!lst || !del) return ; del(lst->content); free(lst); }
void	ft_lstclear(t_list **lst, void (*del)(void *))
{
	t_list *n;
	if (!lst || !del) return ;
	while (*lst) { n = (*lst)->next; ft_lstdelone(*lst, del); *lst = n; }
}
void	ft_lstiter(t_list *lst, void (*f)(void *)) { if (!f) return ; while (lst) { f(lst->content); lst = lst->next; } }
t_list	*ft_lstmap(t_list *lst, void *(*f)(void *), void (*del)(void *))
{
	t_list *r = NULL, *n; void *c;
	if (!f || !del) return (NULL);
	while (lst)
	{
		c = f(lst->content);
		n = ft_lstnew(c);
		if (!n) { del(c); ft_lstclear(&r, del); return (NULL); }
		ft_lstadd_back(&r, n);
		lst = lst->next;
	}
	return (r);
}
