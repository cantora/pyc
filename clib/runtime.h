#ifndef RUNTIME_H
#define RUNTIME_H

#include "hashtable.h"
#include "hashtable_itr.h"
#include "hashtable_utility.h"

/* for old times sake */
void print_int_nl(int x);
int input();

/* Structure and type-tag definitions   */

#define MASK 3    /* 11 */
#define SHIFT 2

#define INT_TAG 0     /* 00 */

#define BOOL_TAG 1   /* 01 */

/* The following is for a non-standard single-precision (21-bit fraction)
   floating point number */
#define FLOAT_TAG 2   /* 10 */

/*
  For larger objects, we have a pointer to the object, and the
  object starts with a tag that says what it is.
*/
#define BIG_TAG 3   /* 11 */

enum big_type_tag { LIST, DICT, FUN, CLASS, OBJECT, UBMETHOD, BMETHOD };

typedef long int pyobj;

struct pyobj_struct;

struct list_struct {
  pyobj* data;
  unsigned int len;
};
typedef struct list_struct list;

typedef struct hashtable* dict;

struct fun_struct {
  void* function_ptr;
  pyobj free_vars;
};
typedef struct fun_struct function;

struct class_struct {
  struct hashtable *attrs;
  int nparents;
  struct class_struct *parents;
};
typedef struct class_struct class;

struct object_struct {
  struct hashtable *attrs;
  class cl;
};
typedef struct object_struct object;

struct unbound_method_struct {
  function fun;
  class cl;
};
typedef struct unbound_method_struct unbound_method;

struct bound_method_struct {
  function fun;
  object receiver;
};
typedef struct bound_method_struct bound_method;


struct pyobj_struct {
  enum big_type_tag tag;
  union {
    dict d;
    list l;
    function f;
    class cl;
    object obj;
    unbound_method ubm;
    bound_method bm;
  } u;
};
typedef struct pyobj_struct big_pyobj;

int tag(pyobj val);

int is_int(pyobj val);
int is_bool(pyobj val);
int is_big(pyobj val);
int is_function(pyobj val);
int is_object(pyobj val);
int is_class(pyobj val);
int is_unbound_method(pyobj val);
int is_bound_method(pyobj val);

pyobj inject_int(int i);
pyobj inject_bool(int b);
pyobj inject_big(big_pyobj* p);

int project_int(pyobj val);
int project_bool(pyobj val);
big_pyobj* project_big(pyobj val);

/* Operations */

int is_true(pyobj v);
void print_any(pyobj p);
pyobj input_int();

big_pyobj* create_list(pyobj length);
big_pyobj* create_dict();
pyobj set_subscript(pyobj c, pyobj key, pyobj val);
pyobj get_subscript(pyobj c, pyobj key);

big_pyobj* add(big_pyobj* a, big_pyobj* b);
int equal(big_pyobj* a, big_pyobj* b);
int not_equal(big_pyobj* x, big_pyobj* y);

big_pyobj* create_closure(void* fun_ptr, pyobj free_vars);
void* get_fun_ptr(pyobj);
pyobj get_free_vars(pyobj);
big_pyobj* set_free_vars(big_pyobj* b, pyobj free_vars);

big_pyobj* create_class(pyobj bases); /* bases should be a list of classes */
big_pyobj* create_object(pyobj cl);
int inherits(pyobj c1, pyobj c2); /* Returns true if class c1 inherits from class c2 */
big_pyobj* get_class(pyobj o); /* Get the class from an object or unbound method */
big_pyobj* get_receiver(pyobj o); /* Get the receiver from inside a bound method */
big_pyobj* get_function(pyobj o); /* Get the function from inside a method */
int has_attr(pyobj o, char* attr);
pyobj get_attr(pyobj c, char* attr);
pyobj set_attr(pyobj obj, char* attr, pyobj val);

pyobj error_pyobj(char* string);

#endif /* RUNTIME_H */
