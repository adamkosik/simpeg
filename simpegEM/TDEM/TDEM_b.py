from BaseTDEM import ProblemBaseTDEM
from FieldsTDEM import FieldsTDEM
import numpy as np

class ProblemTDEM_b(ProblemBaseTDEM):
    """
        Time-Domain EM problem - B-formulation


        .. math::

            \dcurl \e^{(t+1)} + \\frac{\\b^{(t+1)} - \\b^{(t)}}{\delta t} = 0 \\\\
            \dcurl^\\top \MfMui \\b^{(t+1)} - \MeSig \e^{(t+1)} = \Me \j_s^{(t+1)}
    """
    def __init__(self, mesh, model, **kwargs):
        ProblemBaseTDEM.__init__(self, mesh, model, **kwargs)

    solType = 'b'

    ####################################################
    # Internal Methods
    ####################################################

    def getA(self, tInd):
        """
            :param int tInd: Time index
            :rtype: scipy.sparse.csr_matrix
            :return: A
        """

        dt = self.getDt(tInd)
        return self.MfMui*self.mesh.edgeCurl*self.MeSigmaI*self.mesh.edgeCurl.T*self.MfMui + (1/dt)*self.MfMui

    def getRHS(self, tInd, F):
        dt = self.getDt(tInd)
        return (1/dt)*self.MfMui*F.get_b(tInd-1)


    ####################################################
    # Derivatives
    ####################################################

    def J(self, m, v, u=None):
        if u is None:
            u = self.fields(m)
        p = self.G(m, v, u)
        y = self.solveAh(m, p)
        return self.data.projectFields(y)

    def G(self, m, v, u=None):
        if u is None:
            u = self.fields(m)
        p = FieldsTDEM(self.mesh, 1, self.times.size, 'b')
        c = self.mesh.getEdgeMassDeriv()*self.model.transformDeriv(m)*v
        for i in range(self.times.size):
            ei = u.get_e(i)
            pVal = np.empty_like(ei)
            for j in range(ei.shape[1]):
                pVal[:,j] = -ei[:,j]*c

            p.set_e(pVal,i)
            p.set_b(np.zeros((self.mesh.nF,1)), i)
        return p

    def solveAh(self, m, p):
        def AhRHS(tInd, u):
            rhs = self.MfMui*self.mesh.edgeCurl*self.MeSigmaI*p.get_e(tInd) + self.MfMui*p.get_b(tInd)
            if tInd == 0:
                return rhs
            dt = self.getDt(tInd)
            return rhs + 1./dt*self.MfMui*u.get_b(tInd-1)

        def AhCalcFields(sol, solType, tInd):
            b = sol
            e = self.MeSigmaI*self.mesh.edgeCurl.T*self.MfMui*b - self.MeSigmaI*p.get_e(tInd)
            return {'b':b, 'e':e}

        Y = self.fields(m, useThisRhs=AhRHS, useThisCalcFields=AhCalcFields)
        return Y

    ####################################################
    # Functions for tests
    ####################################################

    def AhVec(self, m, u=None):
        if u is None:
            u = self.fields(m)
        self.makeMassMatrices(m)
        dt = self.getDt(0)
        b = 1/dt*u.get_b(0) + self.mesh.edgeCurl*u.get_e(0)
        e = self.mesh.edgeCurl.T*self.MfMui*u.get_b(0) - self.MeSigma*u.get_e(0)
        f = FieldsTDEM(self.mesh, 1, self.times.size, 'b')
        f.set_b(b, 0)
        f.set_e(e, 0)
        for i in range(1,self.times.size):
            dt = self.getDt(i)
            b = 1/dt*u.get_b(i) + self.mesh.edgeCurl*u.get_e(i) - 1/dt*u.get_b(i-1)
            e = self.mesh.edgeCurl.T*self.MfMui*u.get_b(i) - self.MeSigma*u.get_e(i)
            f.set_b(b, i)
            f.set_e(e, i)
        return f

if __name__ == '__main__':
    from SimPEG import *
    import simpegEM as EM
    from simpegEM.Utils.Ana import hzAnalyticDipoleT
    from scipy.constants import mu_0
    import matplotlib.pyplot as plt

    cs = 5.
    ncx = 20
    ncy = 6
    npad = 20
    hx = Utils.meshTensors(((0,cs), (ncx,cs), (npad,cs)))
    hy = Utils.meshTensors(((npad,cs), (ncy,cs), (npad,cs)))
    mesh = Mesh.Cyl1DMesh([hx,hy], -hy.sum()/2)
    model = Model.Vertical1DModel(mesh)

    opts = {'txLoc':0.,
            'txType':'VMD_MVP',
            'rxLoc':np.r_[150., 0.],
            'rxType':'bz',
            'timeCh':np.logspace(-4,-2,20),
            }
    dat = EM.TDEM.DataTDEM1D(**opts)

    prb = EM.TDEM.ProblemTDEM_b(mesh, model)
    # prb.setTimes([1e-5, 5e-5, 2.5e-4], [150, 150, 150])
    # prb.setTimes([1e-5, 5e-5, 2.5e-4], [10, 10, 10])
    prb.setTimes([1e-5], [1])
    prb.pair(dat)
    sigma = np.random.rand(mesh.nCz)

    f = FieldsTDEM(prb.mesh, 1, prb.times.size, 'b')
    for i in range(f.nTimes):
        f.set_b(np.zeros((mesh.nF, 1)), i)
        f.set_e(np.random.rand(mesh.nE, 1), i)

    Ahf = prb.AhVec(sigma, f)
    f_test = prb.solveAh(sigma, Ahf)

    print np.linalg.norm(f.fieldVec() - f_test.fieldVec())

    e0 = f.get_e(0)
    e1 = f_test.get_e(0)
    b0 = f.get_b(0)
    b1 = f_test.get_b(0)
    plt.semilogy(np.abs(e0))
    plt.semilogy(np.abs(e1),'r')
    plt.show()



