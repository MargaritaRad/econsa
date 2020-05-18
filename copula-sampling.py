# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# import numba as nb
import numpy as np
import pandas as pd
import scipy.stats as stats
import chaospy as cp
from pathlib import Path
from multiprocessing import Pool
import matplotlib.pyplot as plt
import seaborn as sns

from econsa.morris import (
    _shift_cov,
    _shift_sample,
    _uniform_to_standard_normal,
    elementary_effects,
)


# # Harris Model from [Sensitivity analysis: A review of recent advances](https://www.sciencedirect.com/science/article/abs/pii/S0377221715005469)

# ## EOQ Function

def eoq_harris(params, x):
    """
    Economic order quantity model by Ford Harris,
    as seen in Borgonovoa & Plischkeb (2016),
    https://doi.org/10.1016/j.ejor.2015.06.032
    Equation: T = (sqrt(S / 2*12*r*M)+sqrt(C))^2,
    or y = sqrt(24*r*x1*x3 / x2)
    
    Args: 
        params (np.array): 2d numpy array,
                           cuurrently only contains interest rate,
                           which is 24*10.
        x (np.array or list): n-d numpy array with the independent variables,
                      currently it only takes 3 dims.
    Output:
        y (np.array): D-d numpy array with the dependent variables
    """
    x_np = np.array(x)
    
    y = np.zeros(x_np.T.shape[0])
    y = np.sqrt((params[0,0] * x_np[0] * x_np[2])/x_np[1])
    
    return(y)


params = np.zeros(shape=(1,1))
params[0,0] = 240
params

# ## Data Generation

# +
# Set flags

seed = 1234
n = 10000
x_min_multiplier = 0.9
x_max_multiplier = 1.1
x0_1 = 1230
x0_2 = 0.0135
x0_3 = 2.15
# -

x_min_multiplier*x0_1, x_max_multiplier*x0_1

# no Monte Carlo
np.random.seed(seed)
x_1 = np.random.uniform(low=x_min_multiplier*x0_1,
                        high=x_max_multiplier*x0_1,
                        size=n)
x_2 = np.random.uniform(low=x_min_multiplier*x0_2,
                                  high=x_max_multiplier*x0_2,
                                  size=n)
x_3 = np.random.uniform(low=x_min_multiplier*x0_3,
                                  high=x_max_multiplier*x0_3,
                                  size=n)
plt.clf()
sns.distplot(x_1)

# ### Monte Carlo with `rvs`

np.random.seed(seed)
x_1 = stats.uniform(x_min_multiplier*x0_1,
                    x_max_multiplier*x0_1).rvs(10000)
x_2 = stats.uniform(x_min_multiplier*x0_2,
                    x_max_multiplier*x0_2).rvs(10000)
x_3 = stats.uniform(x_min_multiplier*x0_3,
                    x_max_multiplier*x0_3).rvs(10000)

plt.clf()
sns.distplot(x_1)

x = np.array([x_1, x_2, x_3])

x

y0 = eoq_harris(params, [x0_1, x0_2, x0_3])
y0

np.array(x)

y = eoq_harris(params, x)

plt.clf()
sns.distplot(y, hist_kws=dict(cumulative=True))

plt.clf()
sns.distplot(y)

# ### Monte Carlo with Chaospy

sample_rule = "random"

np.random.seed(seed)
x_1 = cp.Uniform(x_min_multiplier*x0_1,
                 x_max_multiplier*x0_1).sample(n, rule=sample_rule)
x_2 = cp.Uniform(x_min_multiplier*x0_2,
                 x_max_multiplier*x0_2).sample(n, rule=sample_rule)
x_3 = cp.Uniform(x_min_multiplier*x0_3,
                 x_max_multiplier*x0_3).sample(n, rule=sample_rule)

plt.clf()
sns.distplot(x_1)

x = np.array([x_1, x_2, x_3])
x

y = eoq_harris(params, x)

plt.clf()
sns.distplot(y, hist_kws=dict(cumulative=True))

plt.clf()
sns.distplot(y)

# # Replicating: [Introducing Copula in Monte Carlo Simulation](https://towardsdatascience.com/introducing-copula-in-monte-carlo-simulation-9ed1fe9f905)

# ## Random Variable Transformation

# +
# Generate Monte Carlo sample

x = stats.uniform(0, 1).rvs(10000)
# -

plt.clf()
sns.distplot(x)

norm = stats.distributions.norm()
x_trans = norm.ppf(x)

plt.clf()
sns.distplot(x_trans)

plt.clf()
sns.jointplot(x=x, y=x_trans)

# ## Gaussian Copula — Adding Variable Correlations

mvnorm = stats.multivariate_normal([0, 0], [[1., 0.5], [0.5, 1.]])
x = mvnorm.rvs((10000,))

sns.jointplot(x=x[:,0], y=x[:,1], kind="kde")

norm = stats.norm([0],[1])
x_unif = norm.cdf(x)

plt.clf()
sns.jointplot(x=x_unif[:,0], y=x_unif[:,1], kind="hex")

x1_tri  = stats.triang.ppf(x_unif[:, 0],  c=0.158 , loc=36, scale=21)
x2_norm =stats.norm(525, 112).ppf(x_unif[:, 1])

plt.clf()
sns.distplot(x1_tri)

plt.clf()
sns.distplot(x2_norm)

plt.clf()
sns.jointplot(x=x1_tri, y=x2_norm, kind="hex")

# ## Probabilistic Estimation of HCIIP

# ### No Variable Correlation Case

# +
# HCIIP = GRV*NTG*POR*SHC/FVF

means = [0.]*5
cov = [[1., 0., 0., 0., 0.],
[0., 1., 0., 0., 0.],
[0., 0., 1., 0., 0.],
[0., 0., 0., 1., 0.],
[0., 0., 0., 0., 1.]]

mvnorm_std = stats.multivariate_normal(means,cov)
x = mvnorm_std.rvs(10000,random_state=42)
norm_std = stats.norm()
x_unif = norm_std.cdf(x)

#create individual distr.
grv = stats.triang(c=0.1 , loc=10000, scale=300).ppf(x_unif[:, 0])
ntg = stats.triang(c=0.2 , loc=0.5, scale=0.5).ppf(x_unif[:, 1])
phi = stats.truncnorm(-2*1.96,1.96,0.2,0.05).ppf(x_unif[:, 2])
shc = stats.norm(0.6,0.05).ppf(x_unif[:, 3])
fvf= stats.truncnorm(-1.96,2*1.96,1.3,0.1).ppf(x_unif[:, 4])

stoiip = 7758*grv*ntg*phi*shc/fvf/1e6
# -

plt.clf()
sns.distplot(stoiip, kde=False)

plt.clf()
sns.distplot(stoiip, hist_kws=dict(cumulative=True))

# ### Variable Correlation Case

# +
means = [0.]*5

cov = [[1., 0., 0., 0., 0.],
[0., 1., 0.7, 0.6, 0.],
[0., 0.7, 1., 0.8, 0.],
[0., 0.6, 0.8, 1., 0.],
[0., 0., 0., 0., 1.]]

mvnorm_std = stats.multivariate_normal(means,cov)
x = mvnorm_std.rvs(10000,random_state=42)
norm_std = stats.norm()
x_unif = norm_std.cdf(x)

#create individual distr.
grv = stats.triang(c=0.1 , loc=10000, scale=300).ppf(x_unif[:, 0])
ntg = stats.triang(c=0.2 , loc=0.5, scale=0.5).ppf(x_unif[:, 1])
phi = stats.truncnorm(-2*1.96,1.96,0.2,0.05).ppf(x_unif[:, 2])
shc = stats.norm(0.6,0.05).ppf(x_unif[:, 3])
fvf= stats.truncnorm(-1.96,2*1.96,1.3,0.1).ppf(x_unif[:, 4])

stoiip = 7758*grv*ntg*phi*shc/fvf/1e6
# -

plt.clf()
sns.distplot(stoiip, kde=False)

plt.clf()
sns.distplot(stoiip, hist_kws=dict(cumulative=True))

# # Testing ChaosPy: [Distributions — ChaosPy documentation](https://chaospy.readthedocs.io/en/master/distributions/index.html)

# to create a Gaussian random variable:
distribution = cp.Normal(mu=2, sigma=2)

# to create values from the probability density function:
t = np.linspace(-3, 3, 9)
distribution.pdf(t).round(3)

# create values from the cumulative distribution function:
distribution.cdf(t).round(3)

# To be able to perform any Monte Carlo method,
# each distribution contains random number generator:
distribution.sample(6).round(4)

plt.clf()
sns.distplot(distribution.pdf(t).round(3), kde=False)

# to create low-discrepancy Hammersley sequences
# samples combined with antithetic variates:
distribution.sample(size=6, rule="halton", antithetic=True).round(4)

# ## Moments: [Descriptive Statistics — ChaosPy documentation](https://chaospy.readthedocs.io/en/master/descriptives.html#descriptives)

# the variance is defined as follows:
distribution.mom(2) - distribution.mom(1)**2

# or:
cp.Var(distribution)

# ## Seeding

np.random.seed(1234)
distribution.sample(5).round(4)

distribution.sample(5).round(4)

# ## [Copulas — ChaosPy documentation](https://chaospy.readthedocs.io/en/master/distributions/copulas.html)

np.random.seed(1234)
dist = cp.Iid(cp.Uniform(), 2)
copula = cp.Gumbel(dist, theta=1.5)

copula

np.random.seed(1234)
sample = copula.sample(10000)

plt.clf()
sns.jointplot(x=sample[0], y=sample[1], kind="hex")

# ok, what now…


