function zq = interpolate_vectors(x,y,z,xq,yq)
x = cell2mat(x);
x = cast(x, 'double');
y = cell2mat(y);
y = cast(y, 'double');
z = cell2mat(z);
z = cast(z, 'double');
xq = cell2mat(xq);
xq = cast(xq, 'double');
yq = cell2mat(yq);
yq = cast(yq, 'double');
F = scatteredInterpolant(x',y',z');
zq=F(xq,yq);
end

