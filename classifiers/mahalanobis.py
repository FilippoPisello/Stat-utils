"""Contains MahalanobisClassifier class which allows to categorize observations
based on the computation of the mahanalobis distance from the centers of
of some data categories."""
from typing import Union

import numpy as np
import pandas as pd
from distances.mahalanobis import mahanalobis_from_points


class MahalanobisClassifier:
    def __init__(
        self, dataframe: pd.DataFrame, classifier_col: str, usecols: list[str] = None
    ):
        self.df_all = dataframe
        self.data_columns = usecols if usecols is not None else dataframe.columns
        self.df = dataframe.loc[:, self.data_columns].copy()
        self.class_col = classifier_col

    @property
    def categories(self) -> np.ndarray:
        """Return the unique values on the classifier column."""
        return self.df_all[self.class_col].unique()

    @property
    def category_series(self) -> np.ndarray:
        """Return the series of the classifier column"""
        return self.df_all[self.class_col]

    @property
    def number_categories(self) -> int:
        """Return the number of unique values in the classifier column."""
        return len(self.categories)

    @property
    def number_obs(self) -> int:
        """Return the number of observations in the data frame."""
        return self.df_all.shape[0]

    @property
    def number_vars(self) -> int:
        """Return the number of variables in the data frame."""
        return self.df_all.shape[1]

    # from EXISTING DATA to CATEGORY
    def categorize_training_data(self, sqrt: bool = False) -> pd.Series:
        """Return a pandas series with length N containing the inferred category
        for each observation in the training data frame.

        Parameters
        ----------
        sqrt : bool, optional
            If True, the square root is applied to the distances determining
            the categorization. By default False.

        Returns
        -------
        pd.Series
            Series of length N. First element contains the category for the first
            observation and so on.
        """
        distances = self.distances_from_training_data(sqrt=sqrt)
        return self.categories_from_distances(distances)

    # from NEW DATA to CATEGORY
    def categorize_new_data(
        self, new_data: Union[pd.DataFrame, np.ndarray], sqrt: bool = False
    ) -> pd.Series:
        """Given a set of data with size (N, K), return a pandas series with length
        N containing the mahanalobis categories for the input data.

        The observation is assigned to the category whose center is closest.


        Parameters
        ----------
        new_data : Union[pd.DataFrame, np.ndarray]
            The new data to be classified. If pandas dataframe any number of
            columns is allowed as long as the ones used for centers calculation
            are present. More on KeyError note down here.
            If array, it is assumed that the columns match the order of the ones
            in the original data frame. Array's shape must be (N, K), where K
            is the number of columns used for the original centers calculation.
        sqrt : bool, optional
            If True, the square root is applied to the distances determining
            the categorization. By default False.

        Returns
        -------
        pd.Series
            Series of length N. First element contains the category for the first
            observation and so on.

        Raises
        ------
        KeyError
            Raised if among the columns of the data provided in data frame the
            original data columns are not found.
            Example: if the categories centers were calculated over the columns
            "Foo" "Bar", then "Foo" "Bar" must be within new_data columns.

        """
        data = new_data.copy()
        if isinstance(new_data, pd.DataFrame):
            try:
                data = data.loc[:, self.data_columns]
            except KeyError as e:
                raise KeyError(
                    """The dataframe with new data must have the same
                               data columns as the original one"""
                ) from e
            data = data.to_numpy().squeeze()

        distances = mahanalobis_from_points(
            data, self.means_matrix(), self.cov_matrix(), sqrt=sqrt
        )
        return self.categories_from_distances(distances)

    # from DISTANCES to CATEGORY
    def categories_from_distances(self, distances: np.ndarray) -> pd.Series:
        """Return a pandas series with length N containing the inferred category
        for each element in the distances array.

        The observation is assigned to the category whose center is closest.

        Parameters
        ----------
        distances : np.ndarray
            An array of shape (N, M), containing the distances from M points for
            N observations.

        Returns
        -------
        pd.Series
            Series of length N. First element contains the category for the first
            observation and so on.
        """
        categories_indexes = pd.Series(np.argmin(distances, axis=1), name="Category")
        return categories_indexes.apply(lambda x: self.categories[x])

    # from EXISTING DATA to DISTANCES
    def distances_from_training_data(
        self, sqrt: bool = False, as_dataframe: bool = False
    ) -> Union[np.ndarray, pd.DataFrame]:
        """Return the distances for each variable from the centers of the groups
        identified by the classifier column.

        Parameters
        ----------
        sqrt : bool, optional
            If True, the square root is applied to the distances. By default False.
        as_dataframe : bool, optional
            If True, return the distances in data frame form. Each column matches
            a value from the classifier while each row matches an observation.
            By default False.

        Returns
        -------
        Union[np.ndarray, pd.DataFrame]
            The result has size (N, M) where N is the number of observations while
            M is the number of groups. Each element (x, y) is the distance between
            observation x and the center of group y, where x = [1, ..., N] and
            y = [1, ..., M].
        """
        data = self.df.loc[:, self.data_columns].to_numpy()
        dists = mahanalobis_from_points(
            data, self.means_matrix(), self.cov_matrix(), sqrt
        )
        if as_dataframe:
            dataframe = pd.DataFrame(dists)
            dataframe.columns = self.categories
            return dataframe
        return dists

    def means_matrix(
        self, as_dataframe: bool = False
    ) -> Union[np.ndarray, pd.DataFrame]:
        """Return the means with shape (M, K) where K is the number of variables
        and M is the number of different values attained by the classifier col."""
        means_df = self.df_all.groupby(self.class_col)[self.data_columns].mean()

        if as_dataframe:
            return means_df

        return means_df.to_numpy()

    def cov_matrix(self, as_dataframe: bool = False) -> Union[np.ndarray, pd.DataFrame]:
        """Return the covariances with shape (M, K, K) where K is the number
        of values and M is the number of different values attained by the
        classifier column.

        Each element (z, i, j) of the matrix represents the covariance between
        the variable i and j, conditional to value z. For example, element
        (0, 1, 0) is the covariance between the first and second variable for the
        group of observations with the first value for the categorization column."""
        grouped_df = self.df_all.groupby(self.class_col)

        if as_dataframe:
            return grouped_df[self.data_columns].cov()

        return np.array([group[1][self.data_columns].cov() for group in grouped_df])
