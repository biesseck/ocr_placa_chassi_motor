import torch


def logloss(Ptrue, Pred, szs, eps=1e-10):
    b, h, w, ch = szs
    Pred = torch.clamp(Pred, eps, 1.0 - eps)
    Pred = -torch.log(Pred)
    Pred = Pred * Ptrue
    Pred = Pred.view(b, h * w * ch)
    Pred = torch.sum(Pred, 1)
    return Pred


def l1(true, pred, szs):
    b, h, w, ch = szs
    # res = (true - pred).view(b, h * w * ch)
    res = (true - pred).reshape(b, h * w * ch)
    res = torch.abs(res)
    res = torch.sum(res, 1)
    return res


def clas_loss(Ytrue, Ypred):
    wtrue = 0.5
    wfalse = 0.5
    b, h, w = Ytrue.size(0), Ytrue.size(2), Ytrue.size(3)

    obj_probs_true = Ytrue[:, 0, ...]
    obj_probs_pred = Ypred[:, 0, ...]

    non_obj_probs_true = 1 - obj_probs_true
    non_obj_probs_pred = 1 - obj_probs_pred

    res = wtrue * logloss(obj_probs_true, obj_probs_pred, (b, h, w, 1))
    res += wfalse * logloss(non_obj_probs_true, non_obj_probs_pred, (b, h, w, 1))
    return res


def loc_loss(Ytrue, Ypred):
    b, h, w = Ytrue.size(0), Ytrue.size(2), Ytrue.size(3)

    # device = 'cpu'

    obj_probs_true = Ytrue[:, 0, ...]
    affine_pred = Ypred[:, 1:, ...]
    pts_true = Ytrue[:, 1:, ...]

    affinex = torch.stack([torch.clamp(affine_pred[:, 0, ...], min=0.), affine_pred[:, 1, ...], affine_pred[:, 2, ...]], 1)
    affiney = torch.stack([affine_pred[:, 3, ...], torch.clamp(affine_pred[:, 4, ...], min=0.), affine_pred[:, 5, ...]], 1)

    v = 0.5
    base = torch.tensor([-v, -v, 1., v, -v, 1., v, v, 1., -v, v, 1.])
    base = base.repeat(b, h, w, 1)
    # base = base.reshape(b, -1, h, w)
    base = base.permute(0, 3, 1, 2)

    pts = torch.zeros((b, 0, h, w))

    for i in range(0, 12, 3):
        row = base[:, i:(i + 3), ...]
        ptsx = torch.sum(affinex * row, 1)
        ptsy = torch.sum(affiney * row, 1)

        pts_xy = torch.stack([ptsx, ptsy], 1)
        pts = torch.cat([pts, pts_xy], 1)

    flags = obj_probs_true.view(b, 1, h, w)
    res = 1.0 * l1(pts_true * flags, pts * flags, (b, h, w, 4 * 2))
    return res


def iwpodnet_loss(Ytrue, Ypred):
    wclas = 0.5
    wloc = 0.5
    return wloc * loc_loss(Ytrue, Ypred) + wclas * clas_loss(Ytrue, Ypred)
