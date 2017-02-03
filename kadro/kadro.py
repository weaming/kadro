import numpy as np
import pandas as pd
import itertools as it


class Frame:
    """
    Add a group to the datastructure. Will have effect on .agg/.sort/.mutate methods.
    Calling .agg after grouping will remove it. Otherwise you need to call .ungroup
    if you want to remove the grouping on the datastructure.

        Example:
        import numpy as np
        import pandas as pd
        import kadro as kd

        np.random.seed(42)
        n = 40
        r1 = np.random.rand(n)
        r2 = np.random.rand(n)

        df = pd.DataFrame({
            'a': np.random.randn(n),
            'b': np.random.randn(n),
            'c': ['foo' if x > 0.5 else 'bar' for x in r1],
            'd': ['fizz' if x > 0.5 else 'bo' for x in r2]
        })

        kf = kd.Frame(df)
    """
    def __init__(self, df, groups = []):
        self.df = df.copy()
        """The original pandas representation of the datastructure."""
        self.df.index = np.arange(df.shape[0])
        """The index of the pandas representation. It is ignored by all methods."""
        self.shape = self.df.shape
        """The shape of the pandas representation of the datastructure."""
        self.groups = groups
        """A list containing the groups that are currently specified."""
        self.columns = df.columns
        """The column names of the frame."""

    def __repr__(self):
        res = "Pandas derived TibbleFrame Object.\n"
        if len(self.groups) > 0:
            res += "With groups {}\n".format(self.groups)
        res = res + "\n" + str(self.df.head(10))
        if self.df.shape[0] > 10:
            res = res + "\n only showing top 10 rows."
        return res

    def _group_mutate(self, **kwargs):
        df_copy = self.df.copy()
        res = []
        grouped = df_copy.groupby(self.groups)
        for key in kwargs.keys():
            new_row = pd.concat([group[1].pipe(kwargs[key]) for group in grouped])
            df_copy[key] = new_row
        return Frame(df_copy, self.groups[:])

    def show(self, n = 10):
        """
        Shows the `n` top items of a the datastructure.

            Example:
            kd.show(20)
        """
        res = "Pandas derived TibbleFrame Object.\n"
        if len(self.groups) > 0:
            res += "With groups {}\n".format(self.groups)
        print(res + "\n" + str(self.df.head(n)))

    def plot(self, *args, **kwargs):
        """
        Wrapper around pandas plotting. See pandas documentation.
        """
        return self.df.plot(*args, **kwargs)

    def mutate(self, **kwargs):
        """
        Creates or changes a column. Keeps groups in mind.

            Example:
            kf.mutate(a = lambda _: _['col1'] + _['col2']*2)
        """
        if len(self.groups) != 0:
            return self._group_mutate(**kwargs)
        df_copy = self.df.copy()
        for mut in kwargs.keys():
            df_copy[mut] = kwargs[mut](df_copy)
        return Frame(df_copy, self.groups[:])

    def filter(self, *args):
        """
        Filter rows to keep.

            Example:
            kf.filter(lambda _: _['col1'] > 20)
        """
        df_copy = self.df.copy()
        for func in args:
            predicate = func(df_copy)
            df_copy = df_copy[predicate]
        return Frame(df_copy, self.groups[:])

    def select(self, *args):
        """
        Select a subset of the columns.

        Example:
        kf.select("col1", "col2")
        kf.select(["col1", "col2"])
        """
        columns = list(it.chain(*args))
        df_copy = self.df.copy()
        return Frame(df_copy[columns], self.groups[:])

    def rename(self, rename_dict):
        """
        Renames the dataframe.
        Expects a a dictionary of strings where the keys represent
        the old names and the values represent the new names.

            Example:
            kf.rename({"aa":"a", "bb":"b"})
        """
        df_copy = self.df.copy()
        df_copy = df_copy.rename(index=str, columns = rename_dict)
        return Frame(df_copy, self.groups[:])


    def set_names(self, names):
        """
        Expects a list of strings and will reset the column names.

            Example:
            kf.set_names(["a", "b", "c", "omg_d")
        """
        df_copy = self.df.copy()
        df_copy.columns = names
        return Frame(df_copy, self.groups[:])

    def drop(self, *args):
        """
        Drops columns from the dataframe.

            Example:
            kf.drop("col1")
            kf.drop(["col1", "col2"])
        """
        df_copy = self.df.copy()
        columns = [_ for _ in df_copy.columns if _ not in it.chain(*args)]
        return Frame(df_copy[columns], self.groups[:])

    def sort(self, *args, ascending = True):
        """
        Sort the data structure based on *args passed in.
        Works just like .sort_values in pandas but keeps groups in mind.

            Example:
            kf.sort("col1")
            kf.sort(["col1", "col2"], ascending=[True, False])
        """
        df_copy = self.df.copy()
        sort_cols = self.groups + [arg for arg in args]
        df_sorted = df_copy.sort_values(sort_cols, ascending=ascending)
        return Frame(df_sorted, self.groups[:])

    def group_by(self, *args):
        """
        Add a group to the datastructure. Will have effect on .agg/.sort/.mutate methods.
        Calling .agg after grouping will remove it. Otherwise you need to call .ungroup
        if you want to remove the grouping on the datastructure.

            Example:
            kf.group_by("col1")
            kf.group_by("col1", "col2")
        """
        group_names = [_ for _ in args]
        if any([_ not in self.df.columns for _ in group_names]):
            raise TibbleError("Wrong column name in .group_by method: does not exist.")
        return Frame(self.df.copy(), group_names[:])

    def ungroup(self):
        """
        Removes any group from the datastructure.
        """
        return Frame(self.df.copy(), [])

    def pipe(self, func, *args, **kwargs):
        """
        Pipe the datastructure through a large function. Works just like .pipe in pandas.

            Example:
            def large_function1(frame):
                <stuff>
            def large_function2(frame):
                <stuff>
            kf.pipe(large_function1).pipe(large_function2)
        """
        df_copy = self.df.copy()
        new_df = df_copy.pipe(func, *args, **kwargs)
        return Frame(new_df, self.groups[:])

    def _agg_nogroups(self, **kwargs):
        new_df = pd.DataFrame({k: v(self.df) for k, v in kwargs.items()}, index = [0])
        return Frame(new_df, [])

    def agg(self, **kwargs):
        """
        Aggregates the datastructure. Commonly works with .group_by. If no grouping
        is present it will just aggregate the entire table.

            Examples:
            kd.group_by("col1").agg(m1 = lambda _: np.mean(_['m1']))

            (kd
             .group_by("col1", "col2")
             .agg(m1 = lambda _: np.mean(_['m1']),
                  m2 = lambda _: np.mean(_['m2']),
                  c = lambda _: np.cov(_['m1'], _['m2'])[1,1]))
        """
        if len(self.groups) == 0:
            return self._agg_nogroups(**kwargs)
        df_copy = self.df.copy()
        grouped = df_copy.groupby(self.groups)
        res = [grouped.apply(kwargs[_]) for _ in kwargs.keys()]
        res = pd.concat(res, axis = 1).reset_index()
        res.columns = self.groups + list(kwargs.keys())
        return Frame(res, [])

    def gather(self, key = "key", value="value", keep = []):
        """
        Turns a wide dataframe into a long one. Removes any grouping.

        Example:
        df = pd.DataFrame({
            'a': np.random.random(8),
            'b': np.random.random(8)*3,
            'c': 'a,a,a,a,b,b,b,b'.split(',')
        })
        tf = tb.Tibble(df)
        kf.gather("key", "value")
        """
        copy_df = self.df.copy()
        copy_df = pd.melt(copy_df,
                          id_vars = keep,
                          value_vars=[_ for _ in copy_df.columns if _ not in keep])
        return Frame(copy_df, []).rename({"variable": key, "value": value})

    def spread(self, key = "key", value="key", keep = []):
        """
        Turns a long dataframe into a wide one.

        CURRENTLY UNIMPLEMENTED!
        """
        pass

    def sample_n(self, n_samples, replace = False):
        """
        Samples `n_samples` rows from the datastructure. You can do it with, or without, replacement.

            Example:
            kf.n_sample(100)
            kf.n_sample(1000, replace = True)
        """
        df_copy = self.df.copy()
        idx = np.arange(df_copy.shape[0])
        row_ids = np.random.choice(idx, size = n_samples, replace = replace)
        return Frame(df_copy.iloc[row_ids], self.groups[:])

    def head(self, n = 5):
        """
        Mimic of pandas head function. Selects `n` top rows.

            Example:
            kf.head(10)
        """
        return Frame(self.df.copy().head(n), self.groups[:])

    def tail(self, n = 5):
        """
        Mimic of pandas tail function. Selects `n` bottom rows.

            Example:
            kf.tail(10)
        """
        return Frame(self.df.copy().tail(n), self.groups[:])

    def slice(self, *args):
        """
        Slice away rows of the dataframe based on row number.

        Example:
        kf.slice(1,2,3)
        kf.slice([1,2,3,])
        """
        if len(args) > 1:
            return self.slice(args)
        df_copy = self.df.copy()
        return Frame(df_copy.iloc[args], self.groups[:])

    def _check_join_params(self, other, by):
        if not by:
            by = set(self.columns).intersection(other.columns)
        if len(by) == 0:
            raise ValueError("Columns do not overlap!")
        for i in by:
            if (i not in self.columns) or (i not in other.columns):
                raise ValueError("Column {} does not overlap in both datastructures".format(i))

    def left_join(self, other, by = None):
        self._check_join_params(other, by)
        new = pd.merge(self.df.copy(), other.df.copy(), how = 'left', on = by)
        return Frame(new, self.groups[:])

    def inner_join(self, other, by = None):
        self._check_join_params(other, by)
        new = pd.merge(self.df.copy(), other.df.copy(), how = 'inner', on = by)
        return Frame(new, self.groups[:])